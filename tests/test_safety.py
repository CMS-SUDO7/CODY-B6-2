"""모든 값은 검증용 가짜 자료. 실제 개인정보나 API 호출을 사용하지 않는다."""

import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch
import urllib.error

import gemini_api
import main
from safety import mask_sensitive, prepare_input


class SensitiveInputTests(unittest.TestCase):
    def test_password_names_and_formats(self):
        for name in ("PASSWORD", "password", "dbPassword", "passwd", "pwd", "passphrase",
                     "DB_PASSWORD_2", "api-key", "clientSecret", "access_token", "private-key",
                     "비밀번호", "패스워드", "암호", "비밀 키", "인증키", "토큰"):
            for separator in ("=", ": "):
                for prefix in ("", "+", "-"):
                    with self.subTest(name=name, separator=separator, prefix=prefix):
                        secret = "synthetic-P4ss$word!"
                        self.assertNotIn(secret, mask_sensitive(prefix + name + separator + secret))

    def test_quoted_json_preserves_neighbors(self):
        text = '{"password":"fake-pw", "count":1, "client-secret":"fake-secret", "enabled":true}'
        masked = json.loads(mask_sensitive(text))
        self.assertEqual(masked["password"], "[REDACTED]")
        self.assertEqual(masked["client-secret"], "[REDACTED]")
        self.assertEqual((masked["count"], masked["enabled"]), (1, True))

    def test_escaped_and_multiline_quotes(self):
        for text in ('password="fake\\\"secret"\ncount=1', "password='fake\\'secret'\ncount=1",
                     'password="""\nfake-secret\nsecond-secret\n"""\ncount=1',
                     '+password="""\n+fake-secret\n+second-secret\n+"""\n+count=1',
                     '{"password":\n  "fake-secret",\n  "count":1}'):
            with self.subTest(text=text):
                masked = mask_sensitive(text)
                self.assertNotIn("fake", masked)
                self.assertNotIn("second-secret", masked)
                self.assertIn("count", masked)

    def test_unterminated_quote_masks_remainder(self):
        masked = mask_sensitive('+PASSWORD="""\n+fake-secret\n+second-secret')
        self.assertNotIn("fake-secret", masked)
        self.assertNotIn("second-secret", masked)

    def test_escaped_json_inside_error_message(self):
        embedded = json.dumps({"password": 'fake\\"secret-tail', "count": 1})
        text = json.dumps({"message": embedded})
        masked = mask_sensitive(text)
        self.assertNotIn("fake", masked)
        self.assertNotIn("secret-tail", masked)
        nested = json.loads(json.loads(masked)["message"])
        self.assertEqual(nested["password"], "[REDACTED]")
        self.assertEqual(nested["count"], 1)

    def test_compound_multiline_values(self):
        for text in ('password = (\n "fake-secret"\n "second-secret"\n)\ncount=1',
                     '+tokens = [\n+ "fake-secret",\n+ {"x":"second-secret"}\n+]\n+count=1',
                     '"password": {\n "x": "fake-secret"\n}\ncount=1'):
            with self.subTest(text=text):
                masked = mask_sensitive(text)
                self.assertNotIn("fake-secret", masked)
                self.assertNotIn("second-secret", masked)
                self.assertIn("count=1", masked)

    def test_unlabeled_arbitrary_string_cannot_be_detected(self):
        self.assertEqual(mask_sensitive("unlabeled-opaque-value"), "unlabeled-opaque-value")

    def test_yaml_blocks_and_implicit_multiline(self):
        for indicator in ("|", "|-", ">", ">+", ""):
            for prefix in ("", "+", "-"):
                with self.subTest(indicator=indicator, prefix=prefix):
                    text = (prefix + "  password: " + indicator + "\n" + prefix + "    fake-secret\n"
                            + prefix + "    second-secret\n" + prefix + "  port: 123")
                    masked = mask_sensitive(text)
                    self.assertNotIn("fake-secret", masked)
                    self.assertNotIn("second-secret", masked)
                    self.assertIn("port: 123", masked)

    def test_email_variations(self):
        for email in ("first.last+tag@example.invalid", "o'hara@example.invalid",
                      '"first last"@example.invalid', "사용자@예시.한국", "name@sub.example.invalid"):
            with self.subTest(email=email):
                self.assertEqual(mask_sensitive(email), "[REDACTED]")

    def test_authorization_headers_and_inline_credentials(self):
        for text in ("Authorization: Bearer fake-auth", "authorization=Basic ZmFrZTpzZWNyZXQ=",
                     "+Proxy-Authorization: Basic ZmFrZTpzZWNyZXQ=", "curl -H 'Authorization: Bearer fake-auth'",
                     '"Authorization": "Bearer fake-auth"', "Bearer fake-auth"):
            with self.subTest(text=text):
                masked = mask_sensitive(text)
                self.assertNotIn("fake-auth", masked)
                self.assertNotIn("ZmFrZTpzZWNyZXQ", masked)

    def test_connection_urls_mask_entire_userinfo(self):
        for url in ("postgres://fakeuser:fake!p%40ss@db.invalid/app",
                    "https://fakeuser:fake!p%40ss@host.invalid/", "redis://:fake!p%40ss@localhost:6379/0"):
            with self.subTest(url=url):
                masked = mask_sensitive(url)
                self.assertNotIn("fakeuser", masked)
                self.assertNotIn("fake!p%40ss", masked)
                self.assertIn("[REDACTED]@", masked)

    def test_known_api_keys_and_private_key_blocks(self):
        for key in ("AIza" + "a" * 35, "ghp_" + "a" * 30, "sk-" + "a" * 30, "AKIA" + "A" * 16):
            with self.subTest(key=key):
                self.assertNotIn(key, mask_sensitive(key))
        for prefix in ("", "+", "-"):
            text = (prefix + "-----BEGIN RSA PRIVATE KEY-----\n" + prefix + "fake-private-data\n"
                    + prefix + "-----END RSA PRIVATE KEY-----\ncount=1")
            masked = mask_sensitive(text)
            self.assertNotIn("fake-private-data", masked)
            self.assertIn("count=1", masked)

    def test_all_input_fields_masked_before_building_request(self):
        data, _ = prepare_input("M person@example.invalid", '+password="fake-pass"',
                                "비밀번호: fake-reason-pass", "Authorization: Bearer fake-auth", True, "")
        payload = gemini_api.build_payload(gemini_api.build_prompt("pr", data), 1.0, 2048)
        serialized = json.dumps(payload, ensure_ascii=False)
        for secret in ("person@example.invalid", "fake-pass", "fake-reason-pass", "fake-auth"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 2048)

    def test_multiline_masking_before_diff_size_limit(self):
        diff = '+password="""\n' + "+fake-secret\n" * 220 + '+"""'
        data, _ = prepare_input("M app.py", diff, "", "", True, "")
        self.assertNotIn("fake-secret", data["diff"])

    def test_numeric_output_options_still_visible(self):
        for text in ('max_tokens=2048)', '"maxOutputTokens": 64,', '{"maxOutputTokens":4096}'):
            with self.subTest(text=text):
                self.assertEqual(mask_sensitive(text), text)

    def test_safe_mode_disabled_keeps_input(self):
        # 원문 전송을 허용하는 기존 옵션의 실제 한계도 검증한다.
        data, _ = prepare_input("", "password=fake-secret", "", "", False, "")
        self.assertIn("fake-secret", data["diff"])


class SensitiveCliTests(unittest.TestCase):
    def test_actual_request_body_and_returned_draft_are_masked(self):
        draft = {"title": "person@example.invalid", "summary": "비밀번호: fake-summary",
                 "why": ["passwd=fake-why"], "what": ["postgres://user:fake!pw@db.invalid/app"],
                 "how_to_test": ["Authorization: Bearer fake-auth"]}
        response = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": json.dumps(draft, ensure_ascii=False)}]}}]}
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "mock-api-key"}), \
             patch.object(sys, "argv", ["main.py", "pr", "--reason", "pwd=fake-reason"]), \
             patch("main.collect_changes", return_value=("M person@example.invalid", '+password="fake-input"', 1, 0)), \
             patch("gemini_api.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as send, \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main.main(), 0)
        send.assert_called_once()
        request_data = json.loads(send.call_args.args[0].data)
        prompt = request_data["contents"][0]["parts"][0]["text"]
        for value in ("person@example.invalid", "fake-input", "fake-reason", "mock-api-key"):
            self.assertNotIn(value, prompt)
        for value in ("person@example.invalid", "fake-summary", "fake-why", "fake!pw", "fake-auth"):
            self.assertNotIn(value, out.getvalue() + err.getvalue())

    def test_http_error_masks_password_and_email(self):
        detail = json.dumps({"password": "fake-error-pass", "email": "person@example.invalid"}).encode()
        error = urllib.error.HTTPError("url", 400, "bad", {}, io.BytesIO(detail))
        with patch("gemini_api.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ValueError) as raised:
                gemini_api.generate("prompt", "mock-key", "gemini-test", 1, 2048, 30)
        self.assertNotIn("fake-error-pass", str(raised.exception))
        self.assertNotIn("person@example.invalid", str(raised.exception))

    def test_dry_run_does_not_print_input_secrets(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["main.py", "pr", "--dry-run", "--reason", "pwd=fake-reason"]), \
             patch("main.collect_changes", return_value=("M person@example.invalid", '+password="fake-input"', 1, 0)), \
             contextlib.redirect_stdout(out):
            self.assertEqual(main.main(), 0)
        for value in ("person@example.invalid", "fake-input", "fake-reason"):
            self.assertNotIn(value, out.getvalue())


if __name__ == "__main__":
    unittest.main()
