"""B6-2: Git 변경을 수집하고 Gemini 초안을 출력하는 실행 진입점."""

import json
import os
import sys

from cli import parse_args
from gemini_api import build_payload, build_prompt, generate
from git_changes import collect_changes, run_git
from output_format import format_draft, one_line
from safety import mask_sensitive, prepare_input


def main() -> int:
    """수집 → 마스킹 → 1회 생성 → 형식 보정 → 출력을 수행한다."""
    args = parse_args()
    calls = 0
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    try:
        status, diff, count, untracked = collect_changes()
        if count == 0:
            print("[INFO] 변경 사항이 없습니다.")
            branch = run_git(["status", "--porcelain=v1", "--branch"]).splitlines()[0]
            print("[INFO] " + mask_sensitive(branch.removeprefix("## "), api_key)
                  + "; staged/unstaged/미추적 변경이 없는 상태입니다.")
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
            print("--- 전송 예정 요청 JSON (키 헤더 제외, 전송 안 함) ---\n"
                  + json.dumps(build_payload(prompt, args.temperature, args.max_tokens),
                               ensure_ascii=False, indent=2))
            return 0
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.\n"
                             "[HINT] PowerShell 설정 예시: Set-Item Env:GEMINI_API_KEY \"발급받은_키\"")
        print(f"[INFO] Gemini API 요청 중: {args.model} "
              f"(temperature={args.temperature}, max_tokens={args.max_tokens})", flush=True)
        calls = 1
        draft = generate(prompt, api_key, args.model, args.temperature, args.max_tokens, args.timeout)
        draft["title"] = mask_sensitive(one_line(draft.get("title")), api_key)
        output, notices = format_draft(args.command, draft)
        for notice in notices:
            print("[WARN] " + mask_sensitive(notice, api_key))
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
