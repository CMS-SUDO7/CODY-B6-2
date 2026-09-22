"""실행 예: python main.py pr --safe-mode --staged"""
import argparse
import json
import os
import sys
from ai_client import ENDPOINT, build_payload, request_text
from formatting import DraftFormatError, clean_text, parse_draft, render_draft
from git_context import collect_changes, limit_diff, mask_text, redact_key


def parse_args():
    parser = argparse.ArgumentParser(description='학원 API로 Git 커밋/PR Markdown 초안 생성')
    parser.add_argument('command', choices=['commit', 'pr'])
    parser.add_argument('--model', '-model', default='gpt-5-mini')
    parser.add_argument('--temperature', '-temperature', type=float, default=None, help='명시할 때만 서버에 전송')
    parser.add_argument('--max-tokens', '-max-tokens', type=int, default=None, help='명시할 때만 출력 상한 전송')
    parser.add_argument('--token-parameter', choices=['max_completion_tokens', 'max_tokens'], default='max_completion_tokens')
    parser.add_argument('--timeout', type=int, default=90, help='통신 대기 제한 초')
    parser.add_argument('--max-requests', type=int, choices=[1, 2], default=2, help='형식 정리 포함 최대 요청 수')
    parser.add_argument('--safe-mode', '-safe-mode', action='store_true')
    parser.add_argument('--max-files', type=int, default=10)
    parser.add_argument('--max-lines', type=int, default=200)
    parser.add_argument('--files', nargs='+', default=[], help='분석할 파일 또는 Git 경로 패턴')
    parser.add_argument('--staged', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--reason', default='변경 배경 확인 필요')
    parser.add_argument('--convention', default='한국어, feat/fix/docs/refactor/test/chore 접두어')
    args = parser.parse_args()
    args.model = args.model.strip()
    if not args.model:
        parser.error('model은 비어 있을 수 없습니다.')
    if args.temperature is not None and not 0 <= args.temperature <= 2:
        parser.error('temperature는 0~2여야 합니다.')
    if args.max_tokens is not None and not 1 <= args.max_tokens <= 16000:
        parser.error('max-tokens는 1~16000이어야 합니다.')
    if args.max_files < 1 or args.max_lines < 5:
        parser.error('max-files는 1 이상, max-lines는 5 이상이어야 합니다.')
    if not 1 <= args.timeout <= 300:
        parser.error('timeout은 1~300초여야 합니다.')
    return args


def main():
    args = parse_args()
    calls = 0
    last_text = ''
    try:
        status, diff = collect_changes(args.staged, args.files)
        changes = status.splitlines()[1:]
        print(f'[INFO] Git status: 상태 항목 {len(changes)}개')
        if not changes:
            print('[INFO] 변경 사항이 없습니다.')
            return 0
        if any(line.startswith('?? ') for line in changes):
            print('[WARN] 새 파일 내용은 git add 후 diff에 포함됩니다.')
        if any(line[:2] in {'DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU'} for line in changes):
            raise RuntimeError('병합 충돌을 먼저 해결하세요.')
        if not diff.strip():
            print('[INFO] 선택한 범위에 diff가 없습니다. git add 및 --files 범위를 확인하세요.')
            return 0
        collected = len(diff.splitlines())
        truncated = False
        # 여러 줄 비밀값을 먼저 가린 다음 diff 전송량을 제한한다.
        if args.safe_mode:
            diff = mask_text(diff)
            diff, truncated = limit_diff(diff, args.max_files, args.max_lines)
            status = f'상태 항목 {len(changes)}개; 분석 범위는 아래 diff만 해당'
        print(f'[INFO] Git diff: 수집 {collected}줄 / 전송 {len(diff.splitlines())}줄')
        if truncated:
            print('[WARN] diff 일부만 전송합니다. --files로 대상 파일을 좁히거나 제한값을 조절하세요.')
        context = {'command': args.command, 'status': status, 'diff': diff,
                   'reason': args.reason, 'convention': args.convention, 'truncated': truncated}
        for field in ('reason', 'convention', 'status'):
            context[field] = mask_text(context[field]) if args.safe_mode else redact_key(context[field])
        context['diff'] = redact_key(context['diff'])
        context = json.dumps(context, ensure_ascii=False, indent=2)
        if len(context) > 100_000:
            raise RuntimeError('문맥이 100,000자를 넘습니다. --files 또는 --safe-mode로 범위를 줄이세요.')
        if args.dry_run:
            print('[INFO] API 주소: ' + ENDPOINT)
            print(json.dumps(build_payload(args, context), ensure_ascii=False, indent=2))
            return 0
        # 인증 키는 파일에서 읽지 않고 현재 프로세스의 환경변수에서 읽는다.
        key = os.environ.get('AI_API_KEY', '').strip()
        if not key:
            raise RuntimeError('AI_API_KEY 환경변수가 설정되지 않았습니다. 같은 터미널에서 설정하세요.')
        if not key.isascii() or any(char.isspace() for char in key):
            raise RuntimeError('API 키에 공백 또는 ASCII 이외 문자가 있습니다. 실제 키를 확인하세요.')
        if args.temperature is not None or args.max_tokens is not None:
            print('[INFO] 명시한 temperature/토큰 옵션을 전송합니다. 서버의 지원이 필요합니다.')
        # 문서 형식 오류만 한 번 더 정리하며, 통신 오류는 반복 요청하지 않는다.
        for attempt in range(args.max_requests):
            calls += 1
            print(f'[INFO] AI API 요청 중... ({calls}/{args.max_requests})')
            text, incomplete = request_text(key, args, context, repair=attempt > 0)
            last_text = mask_text(text) if args.safe_mode else redact_key(text)
            if incomplete:
                raise RuntimeError('출력 한도로 응답이 중단됐습니다. 아래 원문은 미완성입니다.')
            try:
                draft = parse_draft(args.command, last_text)
            except DraftFormatError:
                if attempt + 1 >= args.max_requests or len(last_text) > 100_000:
                    raise RuntimeError('초안 형식을 완성하지 못했습니다. 아래 원문을 보존해 직접 검토하세요.')
                print('[WARN] 응답 형식을 한 번 정리합니다. 새 사실을 추가하지 않도록 요청합니다.')
                # 이미 받은 내용만 재정리해 새 변경 사항을 지어내지 않도록 한다.
                context = '다음 원문을 지정 양식으로만 정리하세요:\n' + last_text
                continue
            output, warnings = render_draft(args.command, draft)
            for warning in warnings:
                print('[WARN] ' + warning)
            print('[DONE] 초안 생성 완료: 실제 변경과 대조한 뒤 적용하세요.')
            print(redact_key(output))
            return 0
    except (RuntimeError, OSError) as exc:
        print('[ERROR] ' + redact_key(clean_text(str(exc))), file=sys.stderr)
        if last_text:
            print('--- 자동 처리 전 AI 응답: 검토 필요 ---\n' + last_text)
        return 1
    except KeyboardInterrupt:
        print('[INFO] 사용자가 실행을 중단했습니다.')
        return 130
    finally:
        print(f'[INFO] AI API 호출 시도 횟수: {calls}')


if __name__ == '__main__':
    sys.exit(main())
