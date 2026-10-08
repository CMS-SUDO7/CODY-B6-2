"""네트워크 없이 모듈 계약과 실제 Git 수집을 검증하는 unittest 샘플."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import gemini_api
import git_tools
import main
from output_format import format_draft
from safety import mask_sensitive, prepare_input


def api_response(draft=None, finish="STOP"):
    result = {"candidates": [{"finishReason": finish, "content": {"parts": [
        {"text": json.dumps(draft or {"title": "fix: 입력 검사"}, ensure_ascii=False)}]}}]}
    return io.BytesIO(json.dumps(result).encode("utf-8"))


class GitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="b62-test-")
        self.addCleanup(self.temp.cleanup)
        self.previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, self.previous)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test Sample")
        self.git("config", "user.email", "sample@example.invalid")

    def git(self, *args):
        subprocess.run(["git", *args], check=True, capture_output=True)

    def test_clean_unborn_and_cli(self):
        self.assertEqual(git_tools.collect_changes(), ("", "", 0, 0))
        stream = io.StringIO()
        with patch.object(sys, "argv", ["main.py", "commit"]), contextlib.redirect_stdout(stream):
            self.assertEqual(main.main(), 0)
        self.assertIn("staged/unstaged/미추적 변경이 없는", stream.getvalue())
        self.assertIn("AI API 호출 횟수: 0", stream.getvalue())

    def test_staged_and_unstaged_and_untracked(self):
        Path("app.py").write_text("print(1)\n", encoding="utf-8")
        self.git("add", "app.py")
        Path("app.py").write_text("print(2)\n", encoding="utf-8")
        Path("new.py").write_text("private content", encoding="utf-8")
        status, diff, count, untracked = git_tools.collect_changes()
        self.assertIn("AM app.py", status)
        self.assertIn("+print(1)", diff.split("[UNSTAGED]")[0])
        self.assertIn("+print(2)", diff.split("[UNSTAGED]")[1])
        self.assertNotIn("private content", diff)
        self.assertEqual((count, untracked), (2, 1))

    def test_rename_with_spaces(self):
        Path("old name.py").write_text("print(1)\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "init")
        self.git("mv", "old name.py", "new name.py")
        status, _, count, _ = git_tools.collect_changes()
        self.assertIn("new name.py <- old name.py", status)
        self.assertEqual(count, 1)

    def test_subdirectory_rejected(self):
        Path("child").mkdir()
        os.chdir("child")
        with self.assertRaisesRegex(ValueError, "루트"):
            git_tools.collect_changes()


class ApiTests(unittest.TestCase):
    def test_request_options_and_single_call(self):
        with patch("gemini_api.urllib.request.urlopen", return_value=api_response()) as send:
            self.assertEqual(gemini_api.generate("prompt", "test-key", "gemini-test", 0.2, 123, 30),
                             {"title": "fix: 입력 검사"})
        send.assert_called_once()
        request = send.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload, gemini_api.build_payload("prompt", 0.2, 123))
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 123)
        self.assertEqual(payload["generationConfig"]["temperature"], 0.2)
        self.assertEqual(request.get_method(), "POST")
        self.assertNotIn("test-key", request.data.decode())

    def test_truncated_response_is_not_a_draft_or_retried(self):
        with patch("gemini_api.urllib.request.urlopen", return_value=api_response(finish="MAX_TOKENS")) as send:
            with self.assertRaisesRegex(ValueError, "MAX_TOKENS"):
                gemini_api.generate("prompt", "key", "gemini-test", 1, 64, 30)
        send.assert_called_once()

    def test_network_failure(self):
        with patch("gemini_api.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaisesRegex(ValueError, "네트워크"):
                gemini_api.generate("prompt", "key", "gemini-test", 1, 2048, 30)

    def test_http_key_is_masked(self):
        error = urllib.error.HTTPError("url", 403, "denied", {}, io.BytesIO(b"test-secret"))
        with patch("gemini_api.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ValueError) as raised:
                gemini_api.generate("prompt", "test-secret", "gemini-test", 1, 2048, 30)
        self.assertIn("HTTP 403", str(raised.exception))
        self.assertNotIn("test-secret", str(raised.exception))

    def test_bad_json(self):
        with patch("gemini_api.urllib.request.urlopen", return_value=io.BytesIO(b"not-json")):
            with self.assertRaisesRegex(ValueError, "JSON"):
                gemini_api.generate("prompt", "key", "gemini-test", 1, 2048, 30)


class FormatAndCliTests(unittest.TestCase):
    def test_pr_missing_sections_have_field_guidance(self):
        text, notes = format_draft("pr", {"title": "fix: 입력 검사"})
        for heading in ("Why", "What", "How to Test"):
            self.assertIn("## " + heading, text)
        for field in ("why", "what", "how_to_test"):
            self.assertTrue(any(field + " 권장 작성 예" in note for note in notes))
        self.assertIn("테스트 미실행", text)

    def test_title_limits_and_changes(self):
        for command, limit in (("commit", 72), ("pr", 80)):
            with self.subTest(command=command):
                text, notices = format_draft(command, {"title": "x" * 90,
                                                       "changes": ["a", "b", "c"]})
                self.assertEqual(len(text.splitlines()[0]), limit)
                self.assertTrue(any("title" in notice for notice in notices))
                if command == "commit":
                    self.assertEqual(text.count("\n- "), 2)

    def test_missing_key_hint_and_zero_calls(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), \
             patch.object(sys, "argv", ["main.py", "commit"]), \
             patch("main.collect_changes", return_value=("M app.py", "+print(2)", 1, 0)), \
             patch("main.generate") as send, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main.main(), 1)
        send.assert_not_called()
        self.assertIn('Set-Item Env:GEMINI_API_KEY "발급받은_키"', err.getvalue())
        self.assertIn("AI API 호출 횟수: 0", out.getvalue())

    def test_dry_run_shows_options_without_request(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["main.py", "pr", "--dry-run", "--temperature", "0.2",
                                        "--max-tokens", "128"]), \
             patch("main.collect_changes", return_value=("M app.py", "+print(2)", 1, 0)), \
             patch("main.generate") as send, contextlib.redirect_stdout(out):
            self.assertEqual(main.main(), 0)
        send.assert_not_called()
        self.assertIn('"temperature": 0.2', out.getvalue())
        self.assertIn('"maxOutputTokens": 128', out.getvalue())

    def test_mask_before_input_truncation(self):
        key = "example-long-secret"
        data, omitted = prepare_input("M app.py", "a" * 990 + key + "\n" + "b\n" * 201,
                                      "", "", True, key)
        self.assertTrue(omitted)
        self.assertNotIn(key, json.dumps(data))
        self.assertEqual(mask_sensitive("sample@example.invalid"), "[REDACTED]")

    def test_numeric_output_budget_is_preserved_but_secrets_are_masked(self):
        text = 'max_tokens=2048)\n"maxOutputTokens": 64,\nTOKEN=12345\nmax_tokens=secret'
        masked = mask_sensitive(text)
        self.assertIn("max_tokens=2048)", masked)
        self.assertIn('"maxOutputTokens": 64,', masked)
        self.assertIn("TOKEN=[REDACTED]", masked)
        self.assertIn("max_tokens=[REDACTED]", masked)


if __name__ == "__main__":
    unittest.main()
