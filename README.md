# B6-2: Git 커밋·PR 초안 생성기

Git 변경 내용을 Gemini로 요약하고, 커밋 메시지나 PR 제목·본문을 터미널에 출력하는 Python CLI입니다.
생성한 초안을 검토해 복사하는 방식으로 사용합니다. 커밋, push, PR 등록은 직접 진행합니다.

## 실행 환경

- Python 3.10 이상, Git
- Gemini API 키와 인터넷 연결 — `--dry-run`은 키와 연결 없이 실행 가능
- Python 표준 라이브러리만 사용하므로 별도 패키지 설치 불필요

## 시작하기

### 1. 실행 준비

PowerShell에서 프로젝트 폴더로 이동합니다. 아래 경로는 실제 설치 위치로 바꿉니다.

```powershell
cd C:\study\CODY-B6-2
python --version
git --version
python main.py --help
```

`python`이 인식되지 않으면 Python 설치를 확인하거나 `py -3`로 실행합니다.
Git 저장소가 없는 폴더라면 먼저 `git init`을 실행합니다.

### 2. 전송할 내용 확인

요약할 변경이 있는 **Git 저장소 루트**에서 실행합니다.

```powershell
git status
python main.py commit --dry-run
```

`--dry-run`은 프롬프트와 요청 JSON을 출력합니다. API를 호출하지 않으며 키도 필요 없습니다.
새 파일은 `git diff`에 내용이 나오지 않으므로, 파일을 검토한 뒤 `git add 파일명`으로 스테이징합니다.

### 3. 키 설정과 초안 생성

[Google AI Studio](https://aistudio.google.com/api-keys)에서 키를 발급하고 현재 PowerShell 창에 설정합니다.
`--reason`에는 변경 이유를, `--test`에는 실제로 실행한 테스트와 결과를 적습니다.

```powershell
$env:GEMINI_API_KEY = "발급받은_키"
python main.py commit
python main.py pr --reason "변경 이유" --test "실행한 테스트와 결과"
```

키는 `GEMINI_API_KEY` 환경변수에서만 읽습니다. `.env` 자동 로딩은 지원하지 않으며 새 터미널에서는 다시 설정해야 합니다.
키를 코드나 문서에 저장하지 않고, 키가 보이는 터미널 기록이나 화면은 공유하지 않습니다.
사용 가능한 모델과 무료 할당량, 결제 여부는 AI Studio에서 확인합니다.

macOS/Linux에서는 다음처럼 설정합니다.

```bash
export GEMINI_API_KEY="발급받은_키"
python3 main.py commit
python3 main.py pr
```

### 다른 저장소에서 사용하기

생성기는 다른 폴더에 두어도 됩니다. 요약할 저장소의 루트로 이동한 뒤 `main.py`의 경로를 지정합니다.

```powershell
cd C:\study\mini-redis
python C:\study\CODY-B6-2\main.py commit --dry-run
python C:\study\CODY-B6-2\main.py pr --reason "TTL 동작 설명 보완" --test "README 예제 실행 확인"
```

입력은 **현재 미커밋 변경**입니다. staged와 unstaged diff를 함께 읽으며, 브랜치와 `main` 사이의 커밋 차이는 비교하지 않습니다.
커밋 메시지와 PR 초안이 둘 다 필요하면 실제 커밋 전에 두 명령을 실행해 결과를 복사해 둡니다.
일부만 스테이징했다면 초안에 실제 커밋 범위 밖의 변경이 포함됐는지 확인합니다.
변경이 없으면 API 호출 없이 종료합니다.

## 명령과 옵션

`commit`은 커밋 메시지를, `pr`은 PR 제목·본문을 생성합니다. 옵션은 명령 뒤에 지정합니다.

```powershell
python main.py pr --model gemini-3.1-flash-lite --temperature 0.2 --max-tokens 4096
python main.py pr --dry-run --reason "변경 이유" --test "검증 결과"
```

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--model` | `gemini-3.1-flash-lite` | 사용할 Gemini 모델 |
| `--temperature` | `1.0` | 생성 표현의 다양성 조절, 0~2 |
| `--max-tokens` | `2048` | 출력 토큰 상한, 1~65536. 모델별 제한은 다를 수 있음 |
| `--timeout` | `60` | 네트워크 작업 제한 시간(초), 0 초과~300 이하 |
| `--reason` | 빈 문자열 | 변경 이유. 생략하면 배경 미확인으로 처리 |
| `--test` | 빈 문자열 | 실행한 테스트와 결과. 생략하면 테스트 미실행으로 처리 |
| `--safe-mode` | 켜짐 | 전송 전 민감값 마스킹과 입력 크기 제한 |
| `--no-safe-mode` | 미사용 | 마스킹과 입력 제한 해제. 원문이 전송되므로 샘플 자료에서만 사용 |
| `--dry-run` | 꺼짐 | 프롬프트와 요청 JSON만 출력, API 호출 0회 |

`-model`, `-temperature`, `-max-tokens`, `-safe-mode` 표기도 지원합니다.
옵션별 동작과 실제 비교 결과는 [설계와 옵션 비교](docs/design.md)에 정리했습니다.

## 출력 예시

`app.py`의 `print(1)`을 `print(2)`로 바꾼 뒤 실제 Gemini로 생성한 결과 중 초안 부분입니다.
전체 로그는 [커밋 출력](docs/evidence/live/commit.txt)과 [PR 출력](docs/evidence/live/pr-baseline.txt)에서 확인할 수 있습니다.

커밋 메시지:

```text
chore: app.py 출력값 1에서 2로 변경

- app.py의 print 출력 인자 1을 2로 수정
- python app.py 실행 시 2가 출력되고 종료 코드 0임을 검증 완료
```

PR 제목·본문:

```markdown
app.py 출력값 변경

## Why
- 샘플 출력의 기대값을 1에서 2로 변경하기 위해 수정

## What
- app.py 파일 내 print(1)을 print(2)로 변경

## How to Test
- python app.py 실행 결과 2 출력, 종료 코드 0 확인
```

커밋 제목은 최대 72자, 본문은 불릿 2개까지 출력합니다. PR 제목은 최대 80자이며 `Why`, `What`, `How to Test` 섹션을 붙입니다.
형식은 코드에서 정리하지만 내용의 정확성은 직접 확인해야 합니다. 변경 이유를 추측했거나 실행하지 않은 테스트를 완료했다고 적지 않았는지 검토합니다.

## 안전 모드와 API 호출

안전 모드는 기본으로 켜져 있습니다. status, diff, 변경 이유, 검증 설명에서 키·비밀번호·이메일·개인키 등을 마스킹한 뒤 입력 크기를 제한합니다.

- diff: 앞에서부터 최대 10개 블록, 200줄, 한 줄당 1,000자
- status, diff, reason, test: 항목별 최대 20,000자

같은 파일의 staged/unstaged 변경은 별도 블록으로 셉니다. 입력이 잘리면 경고와 생략 여부를 전달합니다.
전송 전에는 `--dry-run`으로 내용을 확인합니다. 마스킹 범위와 한계는 [민감정보 처리 점검](docs/sensitive_data.md)을 참고합니다.

마스킹은 전송 자료와 터미널 출력에 적용됩니다. 원본 파일, Git index, 커밋 이력은 수정하지 않습니다.
모든 민감값을 탐지하지 못하며, `.gitignore`도 이미 추적 중인 파일을 제외하지 않습니다. 노출된 키는 폐기하고 재발급합니다.

`commit`과 `pr`은 실행당 생성 요청을 1회 시도합니다. 오류가 나도 자동 재시도나 모델 전환은 하지 않습니다.
변경 없음, 키 없음, `--dry-run`에서는 호출하지 않습니다.

## 오류 해결

| 증상 | 확인할 내용 |
| --- | --- |
| `GEMINI_API_KEY` 미설정 | 현재 터미널에서 환경변수 설정 |
| `Git 명령 실패` / 저장소가 아님 | Git 설치와 저장소 위치 확인. 새 저장소는 `git init` 실행 |
| 루트 디렉터리 실행 안내 | `git rev-parse --show-toplevel`로 루트 확인 후 이동 |
| 미추적 파일 경고 | 내용을 검토한 뒤 해당 파일을 `git add` |
| HTTP 400/401/403 | 서버 오류 메시지에 따라 키·옵션·권한·이용 지역 확인 |
| HTTP 404 | 사용 가능한 모델을 `--model`로 지정 |
| HTTP 429 | 할당량과 요청 제한 확인 후 재실행 |
| 네트워크 오류 / 시간 초과 | 연결 상태 확인. 필요하면 `--timeout 120`으로 실행 |
| `MAX_TOKENS` | `--max-tokens 4096` 등으로 출력 상한을 늘려 재실행 |
| 안전 필터 / 결과 없음 / JSON 오류 | `--dry-run`으로 입력 확인 후 재실행 |
| 병합 충돌 | Git에서 충돌을 해결한 뒤 실행 |

종료 코드는 정상 `0`, 실행 오류 `1`, CLI 사용법 오류 `2`, Ctrl+C 중단 `130`입니다.
`--timeout`은 각 네트워크 작업의 제한이며 전체 실행 시간의 상한은 아닙니다.

## 코드와 문서

| 파일 | 역할 |
| --- | --- |
| [main.py](main.py) | CLI 옵션 처리와 실행 흐름, 결과 출력 |
| [git_tools.py](git_tools.py) | Git status와 staged/unstaged diff 수집 |
| [safety.py](safety.py) | 민감값 마스킹과 입력 크기 제한 |
| [gemini_api.py](gemini_api.py) | 프롬프트 구성과 Gemini REST 요청·응답 처리 |
| [output_format.py](output_format.py) | 제목 길이와 커밋·PR 형식 정리 |

테스트는 외부 API 호출 없이 실행합니다.

```powershell
python -m unittest discover -s tests -v
```

- [기초 지식](docs/basic_knowledge.md) · [코드 흐름과 줄별 해설](docs/code_translation.md)
- [설계와 옵션 비교](docs/design.md) · [유지보수 지침](docs/maintenance.md)
- [민감정보 처리 점검](docs/sensitive_data.md)
- [평가 항목과 실행 증거](docs/evaluation.md) · [실제 Gemini 로그](docs/evidence/live/README.md) · [모의 REST 로그](docs/evidence/mock/README.md)
