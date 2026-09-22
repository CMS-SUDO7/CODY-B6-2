# Git 변경 설명 도우미

Git 변경 내용을 학원 AI API에 보내 한국어 **커밋 메시지** 또는 **Pull Request(PR) 초안**을 만드는 Python CLI입니다. 결과는 터미널에 출력되며, 적용하기 전에 사람이 검토합니다. Python 3.10 이상과 Git이 필요하고 외부 Python 패키지는 사용하지 않습니다.

## 시작하기

1. 이 저장소를 내려받거나 복제한 뒤 **Git 저장소 루트**에서 터미널을 엽니다.
2. Python과 Git을 확인합니다.
3. 학원에서 발급받은 API 키를 환경변수 `AI_API_KEY`에 설정합니다. 키를 코드나 Git 추적 파일에 기록하지 마세요.

```bash
python3 --version
git --version
python3 main.py --help
export AI_API_KEY="발급받은_API_키"  # macOS/Linux, 현재 터미널에만 적용
```

Windows PowerShell에서는 다음 명령으로 현재 터미널에 설정합니다.

```powershell
$env:AI_API_KEY = "발급받은_API_키"
python main.py --help
```

## 커밋 메시지와 PR 초안 만들기

먼저 변경을 확인하고, 초안에 포함할 파일을 스테이징합니다. `--staged`는 스테이징한 내용만 읽습니다. 파일을 다시 수정했다면 `git add`도 다시 실행하세요.

```bash
git status --short
git diff --cached
git add README.md
python3 main.py commit --safe-mode --staged --dry-run
python3 main.py commit --safe-mode --staged --reason "README 사용법을 실제 CLI에 맞게 정리"
python3 main.py pr --safe-mode --staged --reason "README 사용법을 실제 CLI에 맞게 정리"
```

PowerShell에서는 `python3` 대신 `python`을 사용하면 됩니다. `--dry-run`은 API 호출 없이 전송 예정 내용을 보여 줍니다. 실제 실행에는 키가 필요합니다. 전체 미커밋 변경을 사용하려면 `--staged`를 빼고, 특정 파일만 분석하려면 `--files README.md`처럼 지정합니다. 새 파일의 내용은 `git add` 전에는 diff에 포함되지 않습니다.

출력 예시는 형식을 보여 주기 위한 것으로 실제 API 응답이 아닙니다.

```text
[INFO] Git status: 상태 항목 1개
[INFO] Git diff: 수집 25줄 / 전송 25줄
[INFO] AI API 요청 중... (1/2)
[DONE] 초안 생성 완료: 실제 변경과 대조한 뒤 적용하세요.
--- Commit Message ---
docs: README 실행 방법 정리

- 환경변수 설정과 커밋·PR 초안 생성 명령을 간결하게 정리
----------------------
[INFO] AI API 호출 시도 횟수: 1
```

```text
--- PR Title ---
docs: README 실행 방법 정리

--- PR Body ---
## Why
- 처음 사용하는 사람이 실행 순서를 쉽게 확인할 수 있도록 문서를 정리

## What
- 환경변수 설정과 CLI 명령 예시를 현재 코드에 맞게 수정

## How to Test
- README의 명령을 실행하고 출력 형식을 확인
----------------------
```

초안은 복사해 검토한 뒤 직접 커밋이나 PR에 적용합니다. **이 도구 자체는 `git commit`, `git push`, GitHub PR 생성을 실행하지 않습니다.** 이미 커밋한 변경은 현재 diff에 없으므로 이 도구의 PR 초안 입력에 포함되지 않습니다.

## 주요 옵션

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `commit` / `pr` | 필수 | 만들 초안 종류 |
| `--staged` | 꺼짐 | 스테이징한 diff만 사용 |
| `--files 경로...` | 전체 | 분석할 diff 파일 선택 |
| `--safe-mode` | 꺼짐 | 대표적인 비밀값을 가리고 전송 범위를 제한 |
| `--max-files`, `--max-lines` | `10`, `200` | 안전 모드의 파일 블록·diff 줄 상한 |
| `--dry-run` | 꺼짐 | 전송 예정 요청 확인, API 호출 없음 |
| `--reason`, `--convention` | 기본 설명·한국어 접두어 | 변경 배경과 팀 표현 규칙 전달 |
| `--model` | `gpt-5-mini` | 사용할 모델 |
| `--temperature`, `--max-tokens` | 생략 | 명시한 경우에만 요청에 추가 |
| `--token-parameter` | `max_completion_tokens` | 토큰 상한 요청 필드 선택 (`max_tokens`도 가능) |
| `--timeout`, `--max-requests` | `90`, `2` | 통신 대기 시간(초), 실행당 최대 요청 횟수 |

전체 옵션은 `python3 main.py commit --help`에서 확인할 수 있습니다. 기본 요청은 `model`과 `messages`만 전송합니다. 선택한 모델과 학원 서버가 추가 파라미터를 지원하는지는 실제 환경에서 확인해야 합니다. 초안 형식을 읽지 못한 경우에만 한 번 더 정리 요청을 보내며, `--max-requests 1`로 제한할 수 있습니다. `commit`과 `pr`은 각각 별도 실행이며 각 실행에서 보통 요청 1회가 발생합니다.

## 전송 범위와 주의사항

`--safe-mode`는 diff의 대표적인 API 키·이메일·비밀값 패턴을 가리고 앞에서부터 최대 10개 파일 블록, 200줄을 선택합니다. 모든 민감정보를 찾아내지는 못하므로 API 호출 전에 `--dry-run` 결과를 확인하세요. 제한 때문에 diff가 잘리면 로그에 수집 줄 수와 전송 줄 수가 따로 표시됩니다. 필요한 경우 `--files`로 범위를 좁히거나 `--max-lines`를 조절하세요.

키가 없거나 선택한 diff가 비어 있으면 API를 호출하지 않습니다. HTTP·네트워크 오류는 자동 재시도하지 않으며 오류 안내와 호출 횟수를 출력합니다. 생성된 문장은 실제 코드 변경과 맞는지 검토하고, `How to Test`의 내용은 실행 기록이 아닌 제안으로 취급하세요.

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `main.py` | CLI 옵션과 실행 흐름 |
| `git_context.py` | Git 상태·diff 수집, 범위 제한과 마스킹 |
| `ai_client.py` | 학원 API 요청과 응답 처리 |
| `formatting.py` | AI 초안 형식 해석과 출력 정리 |
| `docs/basic_knowledge.md` | 관련 Python·Git 기초 |
| `docs/code_translation.md` | 코드 해설 |
