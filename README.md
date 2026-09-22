# 학원 API용 Git 초안 도우미

Git 변경 내용을 읽어 **커밋 메시지 또는 PR 제목·본문**을 만드는 Python CLI입니다. 학원에서 제공한 API 주소와 `gpt-5-mini`를 기본으로 사용합니다. Python 3.10 이상과 Git만 필요하며 외부 Python 라이브러리는 설치하지 않습니다.

## 1. 기존 프로젝트에 적용하고 실행하기

압축 안의 `CODY-B6-2`에서 **main.py, ai_client.py, git_context.py, formatting.py 네 파일을 함께 교체**하세요. README와 docs도 이번 버전으로 교체하면 설명과 코드가 일치합니다. 새 폴더로 시작한다면 압축을 풀고 그 폴더에서 `git init`을 먼저 실행하세요. 기존 저장소에는 다시 실행할 필요가 없습니다.

VS Code에서 프로젝트 폴더를 연 뒤 PowerShell 터미널에서 실행합니다.

```powershell
python --version
git --version
python main.py --help
git add main.py ai_client.py git_context.py formatting.py
```

`git add`는 지금 파일의 내용을 스테이징 영역에 반영합니다. **이미 추가했던 파일도 교체·수정 후에는 다시 git add해야 `--staged`에 새 내용이 들어갑니다.** 이 단계는 커밋하지 않습니다.

이 터미널에 키가 등록돼 있는지는 값을 출력하지 않고 확인할 수 있습니다.

```powershell
Test-Path Env:AI_API_KEY
```

`False`라면 다음 자리표시자를 학원에서 발급받은 실제 키로 바꿔 설정하세요. 이미 유효한 키가 등록돼 있다면 유지하면 됩니다.

```powershell
$env:AI_API_KEY = "학원에서_발급받은_실제_키"
```

먼저 전송할 내용을 확인합니다. 이 실행에는 API 키가 없어도 되고 호출 횟수는 0입니다.

```powershell
python main.py pr --safe-mode --staged --dry-run --files main.py ai_client.py git_context.py formatting.py
```

실제 초안을 생성합니다. 두 명령은 각각 따로 실행합니다.

```powershell
python main.py commit --safe-mode --staged --files main.py ai_client.py git_context.py formatting.py
python main.py pr --safe-mode --staged --reason "Git 변경 내용을 바탕으로 커밋 메시지와 PR 설명을 자동 생성하는 도구 구현" --files main.py ai_client.py git_context.py formatting.py
```

`--files`는 분석 대상을 선택합니다. 위 예시는 코드 네 파일을 선택해 긴 README가 먼저 전송되는 상황을 줄입니다. 선택한 코드가 200줄을 넘으면 일부만 전송될 수 있으므로, 작은 변경 단위로 실행하거나 필요한 경우 `--max-lines 800`처럼 조절하세요. 모든 스테이징 변경을 대상으로 삼으려면 `--files`와 뒤의 파일 목록을 생략합니다.

```powershell
python main.py pr --safe-mode --staged --reason "Git 변경 설명 자동화 도구 구현"
```

완료 메시지와 초안이 나오면 실제 변경과 대조한 뒤 복사해 사용합니다. `How to Test`는 검증 제안이며, 실행한 결과를 증명하는 기록은 아닙니다.

## 2. 이번 버전에서 바뀐 부분

| 이전에 관측된 문제 | 이번 구현 |
| --- | --- |
| 학원 키를 다른 서버에 보내 인증 실패 | 학원 주소 `https://copa.codyssey.kr/v1/chat/completions` 고정 |
| 추가 옵션을 보낸 요청에서 HTTP 400 | 기본 요청은 학원 예제의 `model`·`messages`만 전송 |
| AI가 만든 JSON의 쉼표·따옴표 오류 | AI에는 Markdown 초안 요청. 일반 응답은 JSON 문서로 해석하지 않음 |
| `commit`·`pr` 객체 아래 들어간 제목을 찾지 못함 | 현재 명령에 필요한 양식만 요청. 정상인 과거 JSON 구조는 호환 변환 |
| 제목 표식이나 PR 헤더를 읽지 못함 | 흔한 Markdown 표기를 정리하고, 불명확하면 받은 원문의 형식을 한 번 자동 정리 |
| HTTP 오류 본문을 읽다가 `IncompleteRead`로 종료 | 오류 본문 읽기도 예외 처리하여 HTTP 상태와 안내를 보존 |
| 2900줄 중 얼마를 보냈는지 불분명 | 수집 줄 수와 전송할 diff 줄 수를 따로 표시, `--files` 제공 |

서버와 주고받는 **바깥 요청·응답은 여전히 JSON**입니다. 달라진 부분은 `message.content` 안의 AI 문서에 JSON 문법을 강제하지 않는 것입니다. `response_format` 옵션은 보내지 않습니다.

형식이 정상이라면 API 요청은 1회입니다. 형식을 읽을 수 없을 때만 추가 1회로 정리하고, 그래도 실패하면 받은 텍스트를 화면에 남깁니다. 인증·HTTP·네트워크 오류나 출력 한도로 잘린 응답에는 자동 재시도를 하지 않습니다. `--max-requests 1`이면 추가 형식 정리도 하지 않습니다.

## 3. API 키를 계속 사용하는 방법

이번 미션은 **환경변수 관리**를 사용합니다. 프로그램은 `AI_API_KEY`만 읽으며 `.env` 자동 읽기 기능은 넣지 않았습니다.

PowerShell의 `$env:AI_API_KEY = ...`는 현재 터미널과 그곳에서 시작한 프로그램에 적용됩니다. 새 터미널이나 VS Code를 다시 열면 없어질 수 있습니다. 매번 입력하지 않으려면, 위에서 현재 환경변수에 넣은 키를 Windows 사용자 환경변수에 한 번 저장하세요.

```powershell
[Environment]::SetEnvironmentVariable("AI_API_KEY", $env:AI_API_KEY, "User")
```

현재 터미널에는 이미 값이 있으므로 계속 실행하면 됩니다. 이후에는 VS Code 창을 모두 닫고 다시 시작하면 새 프로세스가 저장된 값을 받습니다. 키를 새로 발급받았다면 현재 환경변수를 새 값으로 바꾼 후 같은 저장 명령을 실행합니다. 환경변수도 비밀 저장소처럼 암호화된 보관 방식을 보장하지 않으므로 공유 PC에서는 계정을 구분해 사용하세요.

macOS/Linux에서는 현재 터미널에 다음처럼 설정합니다.

```bash
export AI_API_KEY="YOUR_ACADEMY_KEY"
```

키의 값은 코드·문서·Git 커밋에 넣지 않습니다. 제공된 `.gitignore`는 환경 파일, 개인키 파일, Python 캐시 등을 제외합니다. 이미 Git이 추적 중인 파일은 ignore 규칙을 추가하는 것만으로 추적이 해제되지는 않습니다.

## 4. 옵션과 기본값

| 옵션 | 기본값 | 동작 |
| --- | --- | --- |
| `commit` / `pr` | 필수 | 생성할 초안 선택 |
| `--model`, `-model` | `gpt-5-mini` | 학원에서 허용한 모델 이름 |
| `--temperature`, `-temperature` | 생략, 서버 기본값 | 0~2. 명시한 경우에만 실제 요청에 추가 |
| `--max-tokens`, `-max-tokens` | 생략, 서버 기본값 | 1~16000. 명시한 경우에만 출력 상한 요청 |
| `--token-parameter` | `max_completion_tokens` | 토큰 옵션의 요청 필드명. `max_tokens`도 선택 가능 |
| `--timeout` | `90` | 1~300초. HTTP 통신 대기 제한 |
| `--max-requests` | `2` | 1 또는 2. 형식 정리를 포함한 최대 호출 수 |
| `--safe-mode`, `-safe-mode` | 꺼짐 | 대표 비밀값 마스킹, diff 파일 블록·줄 수 제한 |
| `--max-files` | `10` | 안전 모드에서 선택할 diff 파일 블록 상한 |
| `--max-lines` | `200` | 안전 모드에서 선택할 diff 줄 상한, 최소 5 |
| `--files` | 전체 | 뒤에 나열한 파일 또는 Git 경로 패턴으로 범위 선택 |
| `--staged` | 꺼짐 | 스테이징 영역만 읽기 |
| `--dry-run` | 꺼짐 | 주소와 실제 전송 예정 JSON 본문 확인, API 호출 없음 |
| `--reason` | 변경 배경 확인 필요 | 사람이 알고 있는 변경 의도 |
| `--convention` | 한국어, 일반적인 커밋 접두어 | 팀의 제목·표현 스타일 |

학원 예제에는 temperature나 토큰 상한 옵션이 없습니다. 따라서 기본 명령에는 이를 넣지 않습니다. 과제의 파라미터 조절 기능은 유지했지만, 학원 서버와 선택 모델이 해당 옵션을 지원해야 실제 적용됩니다. 지원 여부는 이 결과물에서 실서비스로 확인하지 못했습니다.

옵션이 요청에 들어가는지는 호출 없이 확인할 수 있습니다.

```powershell
python main.py pr --safe-mode --staged --dry-run --temperature 0.2 --max-tokens 1500
```

이 명령의 출력 확인은 서버 지원 확인과 다릅니다. 기본 실행에는 출력 토큰 상한을 따로 보내지 않으므로 서버 기본값이 적용되고, 실제 비용은 입력·출력량과 서비스 정책에 따라 달라집니다.

팀 컨벤션은 다음처럼 전달합니다.

```powershell
python main.py pr --safe-mode --staged --convention "한국어, fix(api): 같은 스코프 포함 제목, 간결한 본문"
```

## 5. diff 2900줄은 무슨 뜻인가

숫자는 고정돼 있지 않습니다. Git이 출력한 **변경 내역 텍스트의 줄 수**이며, 추가·삭제 줄과 주변 코드, 파일 헤더, 위치 정보, 이 프로그램의 영역 표식까지 포함합니다. 프로젝트 전체 코드가 반드시 그 줄 수라는 뜻은 아닙니다.

다음 로그라면 2900줄을 수집한 뒤 안전 모드 제한에 따라 diff 200줄을 보낼 예정이라는 뜻입니다. 프롬프트와 변경 이유는 별도로 함께 보냅니다. 키가 없거나 `--dry-run`이면 실제 전송은 하지 않습니다.

```text
[INFO] Git diff: 수집 2900줄 / 전송 200줄
[WARN] diff 일부만 전송합니다. --files로 대상 파일을 좁히거나 제한값을 조절하세요.
```

`git add`한 뒤 파일을 더 수정하면 작업 파일과 스테이징 내용이 달라집니다. `--staged`는 예전에 추가한 내용을 계속 읽기 때문에 같은 줄 수가 반복될 수 있습니다. 줄 수를 없애려고 변경을 커밋할 필요는 없습니다. 현재 변경을 먼저 스테이징하고, 필요한 범위를 선택하세요.

프로그램은 `git status`, `git diff --cached`를 조회합니다. `--staged`를 빼면 `git diff`의 미스테이징 변경도 추가합니다. `--files`는 diff에 적용하고, 상태 항목 수는 저장소 전체 기준입니다. 새 파일은 `git add` 전까지 diff에 내용이 나오지 않습니다.

PR 명령도 **현재 로컬 변경**을 사용합니다. 이미 커밋된 브랜치와 main의 전체 차이를 비교하지 않습니다. 그래서 커밋·PR 초안을 모두 생성한 후 직접 커밋하는 순서가 맞습니다.

## 6. 출력 예시

아래는 양식을 설명하기 위한 예시이며 실제 학원 API 호출 기록이 아닙니다.

```text
[INFO] Git status: 상태 항목 1개
[INFO] Git diff: 수집 12줄 / 전송 12줄
[INFO] AI API 요청 중... (1/2)
[DONE] 초안 생성 완료: 실제 변경과 대조한 뒤 적용하세요.
--- Commit Message ---
fix: API 오류 응답 읽기 개선

- ai_client.py에서 오류 본문 수신 중단 처리 추가
----------------------
[INFO] AI API 호출 시도 횟수: 1
```

```text
--- PR Title ---
fix: API 오류 응답 읽기 개선

--- PR Body ---
## Why
- 서버 오류를 읽는 중 연결이 끊겨도 원인을 확인하기 위함

## What
- ai_client.py에 불완전한 HTTP 오류 본문 처리 추가

## How to Test
- 오류 본문이 중간에 끊기는 모의 응답에서 상태 코드와 안내 출력 확인
----------------------
```

커밋 제목은 50자 이내 권장·최대 72자, PR 제목은 최대 80자입니다. 초과한 제목은 말줄임표와 함께 줄이고 경고합니다. PR의 필수 세 섹션과 각 섹션의 불릿은 후처리로 정리합니다. 빈 섹션에는 `확인 필요`를 표시하고 경고하므로 작성자가 실제 내용으로 보완해야 합니다.

## 7. 오류 처리와 범위

| 상황 | 처리 |
| --- | --- |
| 키 없음 | 요청 0회, 같은 터미널의 환경변수 설정 안내 |
| 변경 없음 / 선택한 diff 없음 | 요청 0회, 정상 종료 |
| HTTP 400 / 401 / 403 / 404 / 429 | 상태별 안내와 읽을 수 있는 서버 상세 출력, 자동 재시도 없음 |
| 네트워크·타임아웃·불완전한 HTTP 응답 | 짧은 오류 안내, 자동 재시도 없음 |
| 읽을 수 없는 AI 문서 형식 | 원문으로 형식 정리 1회, 총 2회 상한 |
| 정리 후에도 형식 오류 | 실패로 종료하고 받은 원문 표시 |
| 출력 한도로 생성 중단 | 미완성임을 알리고 받은 원문 표시 |
| 제목은 있으나 일부 PR 섹션 누락 | 해당 섹션에 확인 필요 불릿과 경고 추가 |

안전 모드는 대표 API/GitHub 키 모양, 이메일, 비밀값 할당, 완전한 개인키 블록을 마스킹한 뒤 앞에서부터 최대 10개 파일 블록·200줄을 선택합니다. 같은 파일이 staged/unstaged 양쪽에 있으면 두 블록으로 셉니다. 파일별로 균등하게 나누지 않으며 마지막 파일 중간에서 잘릴 수 있습니다. 부분 전송 여부도 AI에 알립니다. 실제 환경변수 키는 안전 모드와 관계없이 문맥·출력에서 제거합니다.

마스킹은 모든 비밀값이나 개인정보를 찾는 기능은 아닙니다. 전송할 변경을 `--dry-run`으로 확인하세요. 전체 입력 문맥은 100,000자, API 응답은 2MB를 넘으면 중단합니다. Git 조회의 대기 제한은 15초입니다. HTTP 타임아웃은 통신 대기 제한이며 프로그램 전체 시간이 정확히 그 초 이내라는 뜻은 아닙니다.

Git 루트에서 실행하며, 일반 저장소와 worktree를 대상으로 합니다. 바이너리는 Git이 보여 주는 변경 사실만 알 수 있습니다. 병합 충돌은 먼저 해결해야 합니다. 프로그램은 커밋·push·실제 GitHub PR 생성을 실행하지 않습니다.

종료 코드는 정상·할 일 없음 0, 처리 오류 1, CLI 인수 오류 2, 사용자의 중단 130입니다. 초안과 로그는 stdout, 오류 안내는 stderr입니다. 파일로 리디렉션하면 로그도 함께 저장됩니다.

## 8. 검증 결과와 미션 대응

2026-09-18, Linux / Python 3.12.14에서 임시 Git 저장소와 모의 HTTP 응답을 사용한 **76개 검사 통과**. Python 3.10 문법 검사도 통과했습니다. Windows/Python 3.14에서 직접 실행하거나 학원 키로 실서비스 호출한 검증은 수행하지 못했습니다.

주요 검사는 정상 커밋·PR 전체 실행, 실제 Git의 파일 선택·스테이징 수집, 기본 요청 필드·UTF-8·인증 헤더, 과거 중첩 JSON과 깨진 JSON, 자동 형식 정리 횟수 상한, HTTP 400 오류 본문의 IncompleteRead, 연결 실패, 빈 응답·출력 중단, 길이·섹션 후처리, 키 마스킹입니다. 검증용 모의 응답은 AI 생성 품질이나 학원 서비스 접근을 보증하지 않습니다.

| 미션 요구 | 구현 | 확인 상태 |
| --- | --- | --- |
| Git 루트에서 status/diff 수집, 변경 없음 종료 | git_context.py / main.py | 로컬 검증 |
| 환경변수 키와 REST API 연결 | main.py / ai_client.py | 요청 구성·모의 응답 검증, 실제 호출은 사용자 환경에서 확인 |
| 모델·temperature·토큰 CLI 조절 | main.py / build_payload | 요청 반영 검증, 선택 옵션의 서버 지원 미확인 |
| 커밋 제목·핵심 변경 본문 | formatting.py | 양식 검증 |
| PR 제목과 Why/What/How to Test | formatting.py | 헤더·불릿·누락 처리 검증 |
| 제목 길이·출력 구획·형식 정리 | formatting.py / main.py | 후처리와 최대 1회 정리 요청 검증 |
| 안전 모드와 비용·호출 횟수 안내 | git_context.py / main.py / README | 대표 패턴·범위·호출 수 검증 |
| 설치·키·실행·출력 예시 문서 | README.md / docs | 현재 소스와 대조 |
| GitHub에 소스 push | 본인 저장소에서 직접 수행 | 이 결과물의 코드 생성만으로 완료되지 않음 |

## 9. 실습과 제출 순서

1. 코드 교체 후 `git add`로 반영하고 `--dry-run`에서 범위를 확인합니다.
2. 실제 키가 등록된 터미널에서 커밋과 PR 초안을 각각 생성합니다.
3. 제목·변경 파일·Why·테스트 제안이 실제 변경과 맞는지 확인하고 고칩니다. 두 초안을 복사해 보관합니다.
4. 검토한 파일을 커밋하고 본인 GitHub 저장소에 push합니다. 키가 든 파일이 포함되지 않았는지 스테이징 내용을 확인합니다.

```powershell
git status
git diff --cached
git add main.py ai_client.py git_context.py formatting.py README.md docs .gitignore
git commit -m "feat: 학원 API로 Git 변경 설명 생성"
```

위 제목은 예시입니다. 실제 검토한 제목으로 바꾸세요. 원격이 이미 연결돼 있다면 `git remote -v`와 `git branch --show-current`로 대상 주소와 브랜치를 확인한 후 그 브랜치를 push합니다. 새 저장소라면 GitHub의 빈 저장소 안내에 따라 origin을 연결하세요. 프로그램이 이 단계를 자동 실행하지는 않습니다.

선택 과제는 이전 미션 저장소의 별도 브랜치에서 작은 수정을 만들고 초안 두 개를 생성해 실제 PR을 작성하는 것입니다. PR URL과 AI 초안을 무엇 때문에 수정했는지 5~10줄을 기록합니다. 팀 컨벤션은 `--convention`으로 반영하고 적용 전후를 비교할 수 있습니다. 안전 모드 비교는 키가 없는 연습 데이터로 `--dry-run`을 사용하면 됩니다.

## 10. 파일과 학습 순서

| 파일 | 역할 |
| --- | --- |
| main.py | CLI 옵션, 전체 실행 순서, 오류·호출 수 출력 |
| git_context.py | Git 조회, 전송 범위 선택, 민감 패턴 마스킹 |
| ai_client.py | 학원 API 주소, 프롬프트, HTTP 요청·응답 |
| formatting.py | AI 텍스트 해석, 제목·PR 섹션 후처리 |
| docs/basic_knowledge.md | Python 기초, 미션 핵심, 작은 연습, 추천 도서 |
| docs/code_translation.md | 실제 배포 코드의 줄별 한국어 해설 |

먼저 위 실행 절차로 도구의 입출력을 확인하고, basic_knowledge → main.py의 흐름 → git_context.py → ai_client.py → formatting.py 순서로 읽으세요. 줄별 해설은 코드를 옆에 열어 둔 상태에서 모르는 부분을 찾아보는 용도입니다.
