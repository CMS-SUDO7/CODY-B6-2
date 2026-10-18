"""명령줄 옵션을 해석하고 입력값을 검증한다."""

import argparse
import math
import re


MIN_TEMPERATURE = 0
MAX_TEMPERATURE = 2
MIN_OUTPUT_TOKENS = 1
MAX_OUTPUT_TOKENS = 65536
MAX_TIMEOUT_SECONDS = 300


def parse_args() -> argparse.Namespace:
    """CLI 입력을 해석하고 파라미터 범위를 검증한다."""
    parser = argparse.ArgumentParser(description="Gemini로 Git 변경에서 커밋/PR 초안 생성")
    parser.add_argument("command", choices=["commit", "pr"])
    parser.add_argument("--model", "-model", default="gemini-3.1-flash-lite")
    parser.add_argument("--temperature", "-temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", "-max-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--reason", default="", help="변경 이유. 생략하면 미확인으로 처리")
    parser.add_argument("--test", default="", help="실시한 검증과 결과. 생략하면 미실행으로 처리")
    parser.add_argument("--safe-mode", "-safe-mode", dest="safe_mode", action="store_true", default=True)
    parser.add_argument("--no-safe-mode", dest="safe_mode", action="store_false")
    parser.add_argument("--dry-run", action="store_true", help="전송 예정 입력을 구역별로 확인. API 호출 0회")
    parser.add_argument("--dry-run-format", choices=["text", "json"], default="text",
                        help="--dry-run 출력 형식. text: 읽기 쉬운 입력, json: 전체 요청 본문")
    args = parser.parse_args()
    if args.dry_run_format != "text" and not args.dry_run:
        parser.error("--dry-run-format json은 --dry-run과 함께 사용해 주세요.")
    if not re.fullmatch(r"gemini-[A-Za-z0-9._-]+", args.model):
        parser.error("--model은 gemini-로 시작하는 모델 이름이어야 합니다.")
    if not math.isfinite(args.temperature) or not (
        MIN_TEMPERATURE <= args.temperature <= MAX_TEMPERATURE
    ):
        parser.error(f"--temperature는 {MIN_TEMPERATURE}~{MAX_TEMPERATURE}로 지정해 주세요.")
    if not MIN_OUTPUT_TOKENS <= args.max_tokens <= MAX_OUTPUT_TOKENS:
        parser.error(f"--max-tokens는 {MIN_OUTPUT_TOKENS}~{MAX_OUTPUT_TOKENS}으로 지정해 주세요.")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= MAX_TIMEOUT_SECONDS:
        parser.error(f"--timeout은 0보다 크고 {MAX_TIMEOUT_SECONDS} 이하여야 합니다.")
    return args
