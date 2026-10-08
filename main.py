"""B6-2: Gemini로 Git 커밋 메시지와 PR 초안을 만드는 CLI."""

import argparse
import math
import os
import re
import sys

from gemini_api import build_prompt, generate
from git_tools import collect_changes
from output_format import format_draft, one_line
from safety import mask_sensitive, prepare_input


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
    parser.add_argument("--dry-run", action="store_true", help="전송 내용만 확인. API 호출 0회")
    args = parser.parse_args()
    if not re.fullmatch(r"gemini-[A-Za-z0-9._-]+", args.model):
        parser.error("--model은 gemini-로 시작하는 모델 이름이어야 합니다.")
    if not math.isfinite(args.temperature) or not 0 <= args.temperature <= 2:
        parser.error("--temperature는 0~2로 지정해 주세요.")
    if not 1 <= args.max_tokens <= 65536:
        parser.error("--max-tokens는 1~65536으로 지정해 주세요.")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
        parser.error("--timeout은 0보다 크고 300 이하여야 합니다.")
    return args


def main() -> int:
    """수집 → 마스킹 → 1회 생성 → 형식 보정 → 출력을 수행한다."""
    args = parse_args()
    calls = 0
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    try:
        status, diff, count, untracked = collect_changes()
        if count == 0:
            print("[INFO] 변경 사항이 없습니다.")
            return 0
        print(f"[INFO] Git status 수집 완료: {count}개 항목 변경")
        print(f"[INFO] Git diff 수집 완료: {len(diff.splitlines())}줄 (구분 헤더 포함)")
        if untracked:
            print(f"[WARN] 미추적 {untracked}개 항목은 경로만 확인됩니다. 내용 요약은 먼저 git add 해 주세요.")
        data, omitted = prepare_input(status, diff, args.reason, args.test, args.safe_mode, api_key)
        if omitted:
            print("[WARN] 안전 모드에서 입력 일부를 생략했습니다. 변경 전체를 요약한 결과가 아닙니다.")
        prompt = build_prompt(args.command, data)
        if args.dry_run:
            print("--- 전송 예정 프롬프트 (전송 안 함) ---\n" + prompt)
            return 0
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print(f"[INFO] Gemini API 요청 중: {args.model}", flush=True)
        calls = 1
        draft = generate(prompt, api_key, args.model, args.temperature, args.max_tokens, args.timeout)
        draft["title"] = mask_sensitive(one_line(draft.get("title")), api_key)
        output, notices = format_draft(args.command, draft)
        for notice in notices:
            print("[WARN] " + notice)
        summary = one_line(draft.get("summary")) or "요약이 없습니다. 아래 초안과 diff를 확인해 주세요."
        print("--- 변경 요약 ---\n" + mask_sensitive(summary, api_key))
        label = "Commit Message" if args.command == "commit" else "PR Title / Body"
        print("--- " + label + " ---\n" + mask_sensitive(output, api_key))
        print("----------------------\n[DONE] 생성된 초안을 확인한 뒤 적용해 주세요.")
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError, AttributeError) as error:
        print("[ERROR] " + mask_sensitive(str(error), api_key), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("[ERROR] 사용자가 처리를 중단했습니다.", file=sys.stderr)
        return 130
    finally:
        print(f"[INFO] AI API 호출 횟수: {calls}")


if __name__ == "__main__":
    sys.exit(main())
