# B6-2: AI 기반 Git 커밋·PR 초안 생성기

Git 변경을 읽어 변경 요약, 커밋 메시지 또는 Pull Request(PR) 제목·본문을 터미널에 출력합니다.

## 1. 환경과 파일

- 필요한 환경: Python 3.10 이상, Git, API 호출 시 인터넷 연결.
- 확인 환경: Linux, Python 3.12.14, Git 2.51.1.

| 파일 | 역할 |
| --- | --- |
| `main.py` | CLI 옵션 해석, 흐름 제어, 로그와 결과 출력 |
| `git_tools.py` | 루트 확인, status 및 staged/unstaged diff 수집 |
| `safety.py` | 민감값 마스킹, 안전 모드 입력 제한 |
| `gemini_api.py` | 프롬프트 설계, REST 요청, 응답·오류 처리 |
| `output_format.py` | 제목 길이 보정, PR 헤더와 불릿 생성 |
| `docs/basic_knowledge.md` | 기초 문법, 용어, 설계 이유, 작은 학습 과제, 추천 책 |
| `docs/code_translation.md` | 함수 관계, 입력 추적, 최종 소스 줄별 해설 |
| `docs/git_workflow.md` | 기능별 커밋·브랜치·병합과 GitHub 확인 링크 |
| `.gitignore` | 환경 파일·키 파일·캐시의 신규 추적 방지 |

## 2. 처음 실행하기: Windows PowerShell

압축을 풀고 생성기 폴더로 이동합니다. 아래 `C:\study`는 예시 경로입니다.

```powershell
cd C:\study\b6-2-gemini
python --version
git --version
python main.py --help
```

`python`이 인식되지 않으면 Python을 설치하거나 `py -3`로 바꿉니다. 미션 제출용 저장소가 아직 없다면 이 폴더에서 다음을 실행합니다.

```powershell
git init
git add .
python main.py commit --dry-run
```

이 단계는 API 키 없이 동작합니다. 전송 예정 프롬프트를 출력하고 `AI API 호출 횟수: 0`으로 끝납니다. 변경이 많으면 안전 모드에 의해 일부만 포함될 수 있습니다.

### Gemini 키 설정

1. [Google AI Studio API Keys](https://aistudio.google.com/api-keys)에서 키를 발급합니다.
2. 해당 프로젝트의 무료 사용 가능 모델과 할당량을 확인합니다.
3. 현재 터미널 창에만 환경변수를 설정합니다. 키를 코드나 문서에 붙여 넣지 않습니다.

```powershell
$env:GEMINI_API_KEY = "발급받은_실제_키"
python main.py commit --reason "Git 변경 설명을 자동으로 작성하기 위해 생성기 구현" --test "로컬 모의 검증 완료, 실제 API는 이번 실행으로 확인 예정"
python main.py pr --reason "변경 설명 작성 시간을 줄이기 위해 구현" --test "로컬 검증 결과 확인, 실제 생성 문구는 검토 필요"
```

키는 `GEMINI_API_KEY`만 읽습니다. `.env` 파일을 자동으로 읽지 않습니다. 새 터미널을 열면 위 환경변수를 다시 설정합니다. 키를 입력한 명령이 터미널 기록에 남을 수 있으므로 화면이나 기록을 제출하지 마세요.

macOS/Linux에서는 다음처럼 설정합니다.

```bash
export GEMINI_API_KEY="발급받은_실제_키"
python3 main.py commit
python3 main.py pr
```

### 이전 미션 저장소에서 사용

생성기와 요약할 저장소가 같은 폴더일 필요는 없습니다. **현재 실행 위치**가 요약 대상 Git 저장소의 루트여야 합니다.

```powershell
cd C:\study\mini-redis
git status
# 새 파일 내용은 git diff에 없으므로 검토 후 해당 파일을 먼저 스테이징합니다.
git add README.md
python C:\study\b6-2-gemini\main.py commit --dry-run
python C:\study\b6-2-gemini\main.py pr --reason "TTL 동작 설명 보완" --test "README 예제 명령을 실행해 확인"
```

이미 모든 변경을 커밋했다면 변경 없음으로 종료합니다. 이 도구의 PR 입력은 **현재 미커밋 변경**이며, 브랜치 전체와 main의 커밋 차이를 비교하지 않습니다. 미션의 `git status`/`git diff` 수집 범위에 맞춘 선택입니다. PR 초안은 변경을 커밋하기 전에 생성해 복사해 두세요.

## 3. 명령과 옵션

```powershell
python main.py commit --safe-mode
python main.py pr --model gemini-3.1-flash-lite --temperature 1.0 --max-tokens 4096 --timeout 60
python main.py pr --dry-run --reason "변경 배경" --test "실제로 수행한 검증"
```

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `commit` / `pr` | 필수 | 커밋 메시지 또는 PR 제목·본문 생성 |
| `--model` | `gemini-3.1-flash-lite` | Gemini 모델 이름 |
| `--temperature` | `1.0` | 0~2의 생성 다양성 설정; 품질 점수나 정확도 보장이 아님 |
| `--max-tokens` | `2048` | 출력 토큰 상한, 1~65536; 모델에 따라 더 낮은 제한 가능 |
| `--timeout` | `60` | HTTP 네트워크 작업 시간 제한(초), 0 초과~300 이하 |
| `--reason` | 빈 문자열 | 사용자가 알려 주는 변경 배경 |
| `--test` | 빈 문자열 | 사용자가 실제로 수행한 검증과 결과 |
| `--safe-mode` | 켜짐 | 마스킹과 입력 크기 제한 |
| `--no-safe-mode` | 꺼짐 | 전송 전 마스킹·제한을 해제; 샘플 자료에서만 사용 권장 |
| `--dry-run` | 꺼짐 | 프롬프트만 출력하고 API는 호출하지 않음 |

원문의 `-model`, `-temperature`, `-max-tokens`, `-safe-mode` 표기도 지원합니다. 옵션은 명령 뒤에 둡니다. API 키를 CLI 옵션으로 받지 않습니다.

## 4. 출력 예시

다음은 `app.py`의 출력 값을 1에서 2로 수정한 상황을 위한 **설명용 예시**입니다. 실제 문구는 달라집니다.

```text
[INFO] Git status 수집 완료: 1개 항목 변경
[INFO] Git diff 수집 완료: 10줄 (구분 헤더 포함)
[INFO] Gemini API 요청 중: gemini-3.1-flash-lite
--- 변경 요약 ---
app.py의 출력 값을 변경했습니다.
--- Commit Message ---
fix: 출력 값 수정

- app.py 출력 값을 1에서 2로 변경
----------------------
[DONE] 생성된 초안을 확인한 뒤 적용해 주세요.
[INFO] AI API 호출 횟수: 1
```

PR 출력의 제목·본문 예시입니다. 제목 줄 아래부터 본문이며 로그는 복사할 필요가 없습니다.

```text
--- PR Title / Body ---
fix: 출력 값 수정

## Why
- 변경 배경은 미확인입니다. 작성자가 보충해 주세요.

## What
- app.py의 출력 값을 1에서 2로 변경

## How to Test
- 테스트 미실행: python app.py를 실행해 2가 출력되는지 확인 제안
```

검증 과정은 다음과 같습니다. 제목을 한 줄로 정리하고 커밋 제목은 최대 72자, PR 제목은 최대 80자로 자릅니다. 50자를 넘는 커밋 제목은 권장 길이 경고를 출력합니다. 커밋 본문은 최대 두 개의 불릿을 생성합니다. PR의 `Why`, `What`, `How to Test` 헤더는 Python 코드가 만들고, 각 섹션의 비어 있는 항목에는 미확인/미실행 안내를 보충합니다. 제목이 없거나 JSON이 깨진 경우는 실패로 종료합니다. 형식을 보장하는 것과 내용이 정확한 것은 다르므로 생성 문구를 읽고 고쳐야 합니다.

## 5. 안전 모드와 무료 사용

안전 모드는 기본으로 켜집니다. status, diff, 변경 이유, 검증 설명을 전송 전에 마스킹합니다. 현재 환경변수의 키와 알려진 Gemini/GitHub/OpenAI/AWS 키 형태, 이메일, `API_KEY`/`TOKEN`/`SECRET`/`PASSWORD` 할당 값, PEM 개인키 패턴을 가립니다. 길이 제한 전에 먼저 마스킹하여 잘리는 경계의 키 노출을 줄입니다.

입력은 다음 숫자로 제한합니다.

- diff: 앞에서부터 최대 10개 `diff --git` 블록, 최대 200줄, 한 줄 최대 1,000자.
- status/diff/reason/test: 각각 최대 20,000자. 한 항목이라도 잘리면 `omitted=true`를 전달하고 경고합니다.
- 동일 파일이 staged/unstaged 양쪽에 있으면 두 diff 블록으로 셉니다. 고유 파일 10개를 정확히 세는 정책은 아닙니다.

자료를 전송하기 전에 `--dry-run`으로 확인하세요. 정규표현식은 모든 비밀값이나 개인정보를 알아내지 못하며, 민감 파일을 자동으로 제외하지 않습니다. 안전 모드가 파일 전체를 안전하게 만든다고 보장하지 않습니다. `.gitignore`도 이미 추적 중인 파일은 제외하지 않습니다. 예를 들어 `.env`를 이미 추적했다면 파일을 남기는 `git rm --cached .env`로 추적을 해제하고 `.gitignore`에 추가해야 합니다. 노출된 실제 키는 폐기하고 재발급하세요.

정상적인 `commit`/`pr` 실행은 생성 요청을 각각 **1회만 시도**합니다. API 오류, 출력 형식 오류에도 자동 재시도나 다른 모델로의 자동 전환은 없습니다. 변경 없음/키 없음/dry-run은 0회입니다. 호출 횟수는 클라이언트의 생성 요청 시도 수이고 Google의 청구나 내부 처리를 측정한 값은 아닙니다.

2026-10-08 확인 기준 공식 가격표의 `gemini-3.1-flash-lite` Standard에는 무료 입력·출력 구간이 있습니다. 실제 할당량은 AI Studio에서 확인하세요. 키 자체가 모든 요청의 무료 사용을 보장하지 않습니다. 결제 연결 여부와 모델/프로젝트 제한을 확인하고, 무료 할당량 소진 시 HTTP 429에 따라 기다립니다. 무료 구간의 데이터는 제품 개선에 사용될 수 있으므로 민감한 프로젝트는 전송하지 마세요.

최종 화면과 오류 메시지에도 마스킹을 적용합니다. `--no-safe-mode --dry-run` 조합은 원문을 그대로 보여 주므로 샘플 자료에서만 확인하세요.

## 6. 자주 발생하는 오류

| 증상 | 원인과 해결 |
| --- | --- |
| `GEMINI_API_KEY 환경변수가 설정되지 않았습니다` | 현재 터미널에 환경변수 설정; 키만 `.env`에 쓰는 방법은 지원하지 않음 |
| `Git 명령 실패` / not a git repository | Git 설치, `git init`, 저장소 루트로 이동 |
| `루트 디렉터리에서 실행` | 하위 폴더 대신 저장소 루트에서 실행 |
| 변경 없음 | 커밋 후 작업 폴더가 깨끗하면 정상 종료, API 요청 없음 |
| 미추적 항목 경고 | 새 파일 내용은 diff에 없으므로 검토 후 해당 파일을 `git add` |
| HTTP 400/401/403 | 서버의 구체적 오류와 함께 키·파라미터·권한·지역 확인 |
| HTTP 404 | 모델 이름/가용성 확인 후 `--model`로 변경 |
| HTTP 429 | 할당량 또는 속도 제한; 기다렸다가 재실행 |
| 네트워크 오류/시간 초과 | 인터넷 연결, DNS, 방화벽 확인; 필요 시 `--timeout 120` |
| `MAX_TOKENS` | JSON 생성이 끊김; `--max-tokens 4096` 등으로 늘려 다시 실행 |
| 안전 필터/후보 없음/JSON 오류 | 입력과 모델 확인 후 수동 재실행; 자동 재요청 없음 |
| 병합 충돌 | 충돌 파일을 고치고 Git에서 해결한 뒤 실행 |

정상 종료 코드는 0, 실행 오류는 1, CLI 사용법 오류는 2, 사용자가 Ctrl+C로 중단하면 130입니다. HTTP timeout은 각 네트워크 작업의 제한이며 전체 실행 시간을 정확히 60초로 보장하는 타이머는 아닙니다.

## 7. 요구사항 대응표

| 요구사항 | 구현 파일·함수 | 확인 방법 | 확인 결과 |
| --- | --- | --- | --- |
| Python 3.10 이상 터미널 CLI | `main.py: parse_args/main` | help·컴파일·임시 저장소 실행 | Python 3.12.14 및 Windows/Python 3.14.4 기본 동작 통과, 3.10 직접 실행은 미확인 |
| Git 루트 실행 | `git_tools.py: collect_changes` | 비Git/하위 디렉터리에서 실행 | 거부 확인 |
| status 변경 목록/diff 수집 | `collect_changes/run_git` | 실제 임시 Git 저장소 | 신규·수정·staged+unstaged·rename·빈 파일·binary 확인 |
| 변경 없을 때 종료 | `main` | 빈 저장소에서 키 없이 실행 | 메시지 출력, 요청 0회 |
| 환경변수 키 사용 | `main` | 키 미설정/모의 환경변수 | 누락 안내, 코드에 실제 키 없음 |
| AI API 요청과 출력 | `gemini_api.py: generate`, `main` | urlopen 모의 응답으로 CLI 끝까지 실행 | commit/pr 통과; **실제 Gemini 호출 미확인** |
| 모델/temperature/max_tokens 옵션 | `parse_args`, `generate` | 범위 오류·POST JSON 검사 | 기본값/전달/경계 확인 |
| API 실패 원인 안내 | `generate/main` | HTTP 400/401/403/404/429/500·연결 오류 모의 | 원인 안내, 키 마스킹 확인 |
| 커밋 제목 1줄·본문 불릿 | `build_prompt/format_draft` | 모의 생성/길이 초과 출력 | 최대 72자·권장 경고·불릿 2개 확인 |
| PR 제목·Why/What/How to Test | `format_draft/get_items` | 누락·잘못된 타입을 가진 출력 | 최대 80자·3개 헤더·각 불릿 보충 확인 |
| 구획을 나눈 최종 출력 | `main` | 모의 CLI 출력 | 변경 요약/초안 구분 확인 |
| 실행당 요청 1~2회 이하 | `generate/main` | 요청 호출 수 계측 | 정상/실패 1회; 재시도 없음 |
| 안전 모드 제공 | `safety.py: mask_sensitive/prepare_input` | 키/이메일/PEM/200줄/10블록/장문 | 마스킹과 제한 확인 |
| README 필수 안내 | 이 문서 | 문서 검토 | 설치·키·명령·예시·한도·보안 안내 작성 |
| GitHub 소스 push | 기능별 브랜치와 `main` 병합 | 원격 파일·커밋·브랜치 확인 | [공개 저장소](https://github.com/CMS-SUDO7/CODY-B6-2), [작업 흐름](docs/git_workflow.md) |

## 8. 실제 커밋과 GitHub 제출

도구는 텍스트만 만들고 Git 커밋, push, GitHub PR 생성은 수행하지 않습니다. 원문의 원격 자동 반영 금지 조건에 맞춥니다. 결과를 복사하기 전에 diff에 요약된 변경과 실제 커밋할 변경이 같은지 확인하세요. 두 diff를 모두 요약하므로 일부만 스테이징한 상태의 `git commit`과 초안이 다를 수 있습니다.

이 프로젝트의 실제 공개 등록은 [Git 작업 흐름](docs/git_workflow.md)에 기록한 기능별 브랜치 push와 `--no-ff` 병합 순서로 수행했습니다. 다음 명령은 별도의 새 저장소에 등록할 때 참고하는 기본 예시입니다. `<실제_저장소_URL>`과 예시 메시지는 바꿔야 합니다.

```powershell
git add .
git diff --cached
# 위 diff를 바탕으로 만든 문구를 검토하고, 다음 예시 메시지를 교체합니다.
git commit -m "feat: Gemini 기반 Git 커밋 및 PR 초안 생성기 추가"
git branch -M main
git remote add origin <실제_저장소_URL>
git push -u origin main
```

이미 `origin`이 있으면 중복 등록하지 말고 `git remote -v`로 주소를 확인하세요. 제출 시 저장소 링크와 README를 확인하고, **자신의 키로 실행한 생성 결과**를 추가하세요. API 키가 찍힌 화면은 제출하지 않습니다. 보너스 과제의 실제 PR 1건, 팀 컨벤션 비교, 안전 모드 정책 커스터마이징은 이번 필수 구현 범위에 포함하지 않았습니다.

## 9. 학습 순서와 재현

1. `docs/basic_knowledge.md`의 기초·용어를 읽습니다.
2. 샘플 또는 미션 저장소에서 `--dry-run`을 실행합니다.
3. Gemini 키를 설정하고 `commit` 또는 `pr`를 실행합니다.
4. 핵심 세 가지와 전체 함수 흐름을 읽습니다.
5. `docs/code_translation.md`로 실제 줄을 읽고 작은 수정 과제를 수행합니다.

네트워크 없이 CLI를 확인하려면 변경이 있는 Git 저장소에서 `python main.py commit --dry-run` 또는 `python main.py pr --dry-run`을 실행합니다. API 요청 없이 프롬프트가 출력되고 호출 횟수는 0회입니다.

REST 요청에서 CLI `--max-tokens`는 Gemini의 `maxOutputTokens`로 연결됩니다. 응답은 HTTP 응답 JSON 안의 `candidates[0].content.parts`에서 텍스트를 모은 뒤, AI가 쓴 JSON을 다시 해석합니다. 스키마 강제가 아니라 JSON MIME 요청과 프로그램의 후처리를 사용합니다.
