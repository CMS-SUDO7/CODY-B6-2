"""실제 CLI 실행 로그를 저장한다. 기본은 모의 REST, --live는 실제 Gemini 호출."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import runpy
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safety import mask_sensitive

REASON = "샘플 출력의 기대값을 1에서 2로 변경하기 위해 수정"
TEST = "python app.py 실행 결과 2 출력, 종료 코드 0 확인"


def mock_worker(arguments: list[str]) -> int:
    """HTTP 계층만 고정 응답으로 대체하고 실제 main/Git/후처리를 실행한다."""
    draft = {
        "summary": "app.py의 출력 값을 1에서 2로 변경했습니다.",
        "title": "fix: 샘플 출력 값을 2로 변경",
        "changes": ["app.py의 print(1)을 print(2)로 변경"],
        "why": [REASON], "what": ["app.py의 print(1)을 print(2)로 변경"],
        "how_to_test": [TEST],
    }
    response = {"candidates": [{"finishReason": "STOP", "content": {
        "parts": [{"text": json.dumps(draft, ensure_ascii=False)}]}}]}
    print("[EVIDENCE] 모의 REST 응답 사용 / 외부 Gemini 호출: 0회")
    sys.argv = [str(ROOT / "main.py"), *arguments]
    with patch("urllib.request.urlopen", return_value=io.BytesIO(
            json.dumps(response, ensure_ascii=False).encode("utf-8"))):
        runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
    return 0


def run(command: list[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=150)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="실제 생성 요청 5회, 자동 재시도 없음")
    parser.add_argument("--key-file", type=Path, help="검증 전용 로컬 키 파일. 로그에는 값을 기록하지 않음")
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    args = parser.parse_args()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if args.key_file:
        # dotenv 전체 지원이 아니라 검증용 단일 키만 읽는다. 쉘 명령으로 실행하지 않는다.
        for line in args.key_file.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name == "GEMINI_API_KEY":
                env[name] = value.strip().strip("\"'")
    api_key = env.get("GEMINI_API_KEY", "").strip() if args.live else "mock-key-for-local-evidence"
    if args.live and not api_key:
        parser.error("GEMINI_API_KEY가 필요합니다. 환경변수 또는 --key-file .env를 설정하세요.")
    env["GEMINI_API_KEY"] = api_key
    mode = "live" if args.live else "mock"
    out = ROOT / "docs" / "evidence" / mode
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    records = []

    with tempfile.TemporaryDirectory(prefix="b62-evidence-") as directory:
        sample = Path(directory)
        git = lambda *items: run(["git", *items], sample, env)
        for command in (("init", "-b", "main"), ("config", "user.name", "Evidence Sample"),
                        ("config", "user.email", "sample@example.invalid")):
            result = git(*command)
            if result.returncode:
                raise RuntimeError(result.stderr)
        (sample / "app.py").write_text("print(1)\n", encoding="utf-8")
        git("add", "app.py").check_returncode()
        git("commit", "-m", "chore: initialize evidence sample").check_returncode()

        def capture(name: str, arguments: list[str], mock: bool = False,
                    key: bool = True) -> subprocess.CompletedProcess:
            execution_env = dict(env)
            if not key:
                execution_env.pop("GEMINI_API_KEY", None)
            if mock:
                command = [sys.executable, str(Path(__file__).resolve()), "--mock-worker", *arguments]
            else:
                command = [sys.executable, str(ROOT / "main.py"), *arguments]
            result = run(command, sample, execution_env)
            stdout = mask_sensitive(result.stdout, api_key)
            stderr = mask_sensitive(result.stderr, api_key)
            log = (f"Captured at: {timestamp}\nMode: {mode}\n"
                   f"Command: python main.py {' '.join(arguments)}\n"
                   f"Exit code: {result.returncode}\n\n--- stdout ---\n{stdout}"
                   f"\n--- stderr ---\n{stderr}")
            (out / f"{name}.txt").write_text(log, encoding="utf-8")
            title = ""
            for label in ("--- Commit Message ---\n", "--- PR Title / Body ---\n"):
                if label in stdout:
                    title = stdout.split(label, 1)[1].splitlines()[0]
            records.append({"case": name, "arguments": arguments, "exit_code": result.returncode,
                            "title": title, "stdout_chars": len(stdout)})
            print(f"[{mode}] {name}: exit={result.returncode}", flush=True)
            return result

        capture("no-changes", ["commit"], key=False).check_returncode()
        (sample / "app.py").write_text("print(2)\n", encoding="utf-8")
        result = run([sys.executable, "app.py"], sample, env)
        if result.returncode != 0 or result.stdout.strip() != "2":
            raise RuntimeError("샘플 검증 실패")
        git("add", "app.py").check_returncode()
        diff = git("diff", "--cached").stdout
        digest = hashlib.sha256(diff.encode("utf-8")).hexdigest()
        (out / "input.diff").write_text(diff, encoding="utf-8")
        missing = capture("missing-key", ["commit"], key=False)
        if missing.returncode != 1 or "PowerShell" not in missing.stderr:
            raise RuntimeError("키 미설정 안내 검증 실패")
        dry = capture("request-preview", ["pr", "--dry-run", "--temperature", "0.2",
                      "--max-tokens", "2048", "--reason", REASON, "--test", TEST])
        dry.check_returncode()
        marker = "--- 전송 예정 요청 JSON (키 헤더 제외, 전송 안 함) ---\n"
        payload, _ = json.JSONDecoder().raw_decode(dry.stdout.split(marker, 1)[1])
        (out / "request.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
        cases = [("commit", "commit", "1.0", "2048"), ("pr-baseline", "pr", "0.2", "2048")]
        if args.live:
            cases += [("pr-temperature", "pr", "1.2", "2048"),
                      ("pr-small-budget", "pr", "0.2", "64"),
                      ("pr-large-budget", "pr", "0.2", "4096")]
        for name, command, temperature, tokens in cases:
            capture(name, [command, "--model", args.model, "--temperature", temperature,
                          "--max-tokens", tokens, "--timeout", "120", "--reason", REASON,
                          "--test", TEST], mock=not args.live)
        metadata = {"captured_at": timestamp, "mode": mode, "python": platform.python_version(),
                    "platform": platform.system(), "git": git("--version").stdout.strip(),
                    "model": args.model, "diff_sha256": digest, "sample_test": TEST, "cases": records}
        (out / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
        report = ["# 실행 기록", "", f"기록 시각: {timestamp}", "",
                  "실제 Gemini REST 호출 결과입니다." if args.live else
                  "실제 CLI·Git 실행에 모의 REST 응답을 연결했습니다. 외부 Gemini 호출은 0회입니다.", "",
                  f"입력 diff SHA-256: `{digest}`. 모든 생성 실행에 같은 diff/reason/test를 사용했습니다.", "",
                  "| 실행 로그 | 종료 코드 | stdout 문자 수 | 제목 |", "| --- | --- | --- | --- |"]
        for record in records:
            report.append(f"| [{record['case']}]({record['case']}.txt) | {record['exit_code']} | "
                          f"{record['stdout_chars']} | {record['title']} |")
        report += ["", "stdout 문자 수는 로그를 포함하므로 토큰 수나 품질 점수가 아닙니다.", ""]
        if args.live:
            report += ["pr-baseline ↔ pr-temperature는 temperature만, pr-baseline ↔ pr-small-budget/"
                       "pr-large-budget는 max_tokens만 바꿨습니다. 각 조건 1회라 인과관계·재현성을 입증하지는 않습니다.", "",
                       "작은 예산이 실패하면 오류 로그에서 MAX_TOKENS를 확인하세요. 예산을 늘려도 답변이 반드시 "
                       "길어지지는 않습니다. 두 성공 초안의 표현·내용 차이는 원문 로그를 직접 비교하세요.", ""]
        (out / "README.md").write_text("\n".join(report), encoding="utf-8")
    required = {"commit", "pr-baseline"}
    if args.live:
        required |= {"pr-temperature", "pr-large-budget"}
    return int(any(item["exit_code"] != 0 for item in records if item["case"] in required))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mock-worker":
        sys.exit(mock_worker(sys.argv[2:]))
    sys.exit(main())
