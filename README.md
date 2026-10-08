# B6-2: AI 기반 Git 커밋·PR 초안 생성기  

Git 변경을 읽어 변경 요약, 커밋 메시지 또는 Pull Request(PR) 제목·본문을 터미널에 출력합니다.  

사전평가 보완 내용과 실행 증거는 [평가 항목별 안내](docs/evaluation.md)에 정리했습니다. [실제 Gemini 실행 로그](docs/evidence/live/README.md)에 commit·PR 생성과 옵션 비교 결과를 저장했습니다. [모의 REST를 연결한 실제 CLI 로그](docs/evidence/mock/README.md)는 외부 API 없이 재현할 수 있습니다. 실제 Gemini 로그는 `python scripts/capture_evidence.py --live`로 별도 기록합니다.

## 1. 환경과 파일  

- 필요한 환경: Python 3.10 이상, Git, API 호출 시 인터넷 연결.  
- 외부 패키지 없이 Python 표준 라이브러리만 사용합니다. `pip install`은 필요 없습니다.
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

### 옵션을 제공하는 이유와 실험 방법

모델 이름을 코드에 고정하면 모델 접근 권한이나 버전이 바뀔 때 소스를 수정해야 합니다. `--model`로 실행 당시 모델을 명시하고, `--temperature`로 표현 다양성, `--max-tokens`로 응답 예산을 조절하면 목적에 맞는 실험과 문제 재현이 가능합니다. 같은 diff, 프롬프트, 모델 이름, 옵션, 실행 시각을 기록해야 비교 조건을 알 수 있습니다. 같은 설정도 서버 모델 갱신과 샘플링 때문에 같은 문구를 보장하지 않습니다. 낮은 temperature를 고정한 실행은 변동을 줄이는 실험 조건이며 완전한 재현성 보장은 아닙니다.

```powershell
# 같은 미커밋 diff에서 temperature만 변경: 표현의 다양성 비교
python main.py pr --temperature 0.2 --max-tokens 2048
python main.py pr --temperature 1.2 --max-tokens 2048
# temperature를 유지하고 출력 예산만 변경: 완결 여부 비교
python main.py pr --temperature 0.2 --max-tokens 64
python main.py pr --temperature 0.2 --max-tokens 4096
```

temperature는 다음 토큰 선택 확률의 분포를 조절합니다. 일반적인 샘플링 모델에서는 `p(i) ∝ exp(logit(i)/T)`이므로 T를 낮추면 가능성이 큰 후보에 집중하고 높이면 후보 분포가 평평해집니다. T=0은 이 식에 직접 대입하지 않는 별도 극한/선택 처리입니다. 모델별 구현·권장값은 다를 수 있습니다. [공식 생성 설정](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig)

예를 들어 같은 `print(1) → print(2)` diff에서 낮은 값은 `fix: 출력 값 변경`, 높은 값은 `fix: 샘플 출력의 기대값을 2로 조정`처럼 표현 후보를 넓힐 수 있습니다. 이는 **설명용 예시**이며 실제 관측 결과가 아닙니다. 창의성은 표현 다양성의 의미로 사용합니다. 결과 결합도는 제목·Why·What·검증이 같은 변경 사실을 일관되게 설명하는 정도입니다. temperature를 높인다고 결합도가 좋아지지는 않으며 배경 추측이나 항목 간 불일치가 늘 수도 있습니다. 결합도는 diff/reason/test 제공과 수동 사실 확인으로 평가해야 합니다. 모델의 권장값을 기준으로 비교하고 한 번의 결과 차이를 일반화하지 마세요.

`max_tokens`는 생성 길이의 목표가 아닌 상한이며 REST의 `maxOutputTokens`에 연결됩니다. 입력 프롬프트도 토큰을 사용하고 모델은 입력 한도와 출력 한도를 제공합니다. 이 도구는 문자·줄 수만 제한하므로 실제 토큰 수나 모델 한도를 검증하지 않습니다. 정확한 입력 수는 모델의 `countTokens`, 실제 사용량은 응답의 `usageMetadata`로 확인할 수 있습니다. [공식 토큰 안내](https://ai.google.dev/gemini-api/docs/tokens)

토큰 예산을 설명하기 위한 가상 모델이 총 컨텍스트 C=8,192, 출력 한도 O=2,048을 공유한다고 가정하면 입력 I=7,000일 때 출력 공간은 `min(O, C-I)=1,192`입니다. 이 계산은 공유 한도 모델의 학습용 예시로, Gemini의 실제 모델별 한도를 대체하지 않습니다. 현재 사용하는 모델의 입력·출력 한도를 각각 확인해야 합니다. 출력 64토큰으로 PR JSON을 만들다가 `{"title":"...","why":[`에서 멈추는 것도 설명용 절단 예시입니다. 실제 응답이 `MAX_TOKENS`이면 초안을 성공으로 출력하지 않고 오류로 종료합니다. 입력 한도 초과는 출력 예산을 늘려 해결하지 못하므로 diff를 줄여야 합니다. 사고 기능이 있는 모델에서는 사고 토큰도 출력 예산을 소비할 수 있습니다. [공식 사고 토큰 안내](https://ai.google.dev/gemini-api/docs/thinking)

실제 옵션 비교 로그를 재현하려면 `python scripts/capture_evidence.py --live`를 실행합니다. 동일한 샘플 diff에서 기준 PR(0.2/2048), temperature 변경(1.2/2048), 작은 예산(0.2/64), 큰 예산(0.2/4096)을 기록합니다. 종료 코드·제목·전체 stdout/stderr를 보존하며, 작은 예산의 실패도 증거로 남깁니다. 자세한 방법은 [실행 증거 안내](docs/evaluation.md)를 참고하세요.

2026-10-08 15:59 KST에 시작한 실제 Gemini 비교 결과입니다. 모델은 `gemini-3.1-flash-lite`, 입력은 `app.py`의 `print(1) → print(2)`로 고정했습니다. 각 조건을 1회 실행했습니다.

| temperature | max_tokens | 실제 결과 | 원문 로그 |
| --- | --- | --- | --- |
| 0.2 | 2048 | 종료 0, 제목 `app.py 출력값 변경`, PR 3개 섹션 완성 | [기준 PR](docs/evidence/live/pr-baseline.txt) |
| 1.2 | 2048 | 종료 0, 제목 `app.py 샘플 출력 기대값 변경`, PR 3개 섹션 완성 | [temperature 변경](docs/evidence/live/pr-temperature.txt) |
| 0.2 | 64 | 종료 1, `MAX_TOKENS`, 미완료 초안 출력 없음 | [작은 예산](docs/evidence/live/pr-small-budget.txt) |
| 0.2 | 4096 | 종료 0, 기준 PR과 같은 제목·본문 | [큰 예산](docs/evidence/live/pr-large-budget.txt) |

temperature 비교에서 제목·요약의 표현 차이를 관측했지만 각 조건 1회라 설정의 일반적인 효과를 입증하지는 않습니다. 64토큰은 이 입력의 PR을 완성하기에 부족했고, 2048과 4096은 충분했습니다. 큰 예산에서도 결과가 같았으므로 상한을 늘리면 반드시 글이 길어지는 것은 아니라는 점을 이 실행에서 확인했습니다.

## 4. 출력 예시  

실제 API 실행에서 기록한 [커밋 출력](docs/evidence/live/commit.txt)과 [PR 제목·본문 출력](docs/evidence/live/pr-baseline.txt)을 제출 증거로 확인할 수 있습니다. 두 실행 모두 종료 코드 0, 생성 요청 시도 1회입니다. 아래 예시는 형식을 설명하기 위한 별도 자료입니다.

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

### 프롬프트와 후처리를 분리한 이유

`build_prompt`는 diff/status/reason/test를 근거로 내용과 출력 필드를 요청하고, `format_draft`는 반환된 JSON의 제목 길이와 PR 섹션 구조를 정리합니다. 모델이 규칙을 항상 지킨다는 가정을 줄이고 형식 규칙을 네트워크 없이 독립적으로 검사하기 위한 분리입니다. 프롬프트 수정은 요약 품질에, 후처리 수정은 복사할 텍스트의 형태에 집중할 수 있습니다. 대신 두 단계의 필드 이름을 함께 관리해야 하며, 후처리는 배경·검증 결과의 사실 여부를 알아낼 수 없습니다. 제목을 자르면 의미가 손실될 수도 있어 보정 경고와 수동 검토를 유지합니다.

| 방식 | 정확도·제어성 | 비용·한계 |
| --- | --- | --- |
| 후처리(현재 선택) | 같은 응답에 일관된 길이·헤더 규칙 적용, 누락 사실은 미확인/미실행 표시 | 추가 API 비용·대기 없음. 사실 오류를 고치지 못하고 잘린 제목 의미 검토 필요 |
| 자동 재생성 | 규칙과 누락 내용을 다시 요청할 수 있지만 사실 정확도나 형식 준수는 보장되지 않음 | 응답이 바뀌어 검토 범위 증가, 추가 지연·할당량 사용, 반복 제한과 호출 수 관리 필요 |

현재 과제는 적은 호출로 검토 가능한 초안을 만드는 것이므로 후처리를 선택했습니다. 잘못된 JSON·빈 제목·미완료 생성은 성공 초안으로 꾸미지 않고 실패로 알립니다. 재생성이 필요하면 사용자가 입력·설정을 수정하고 수동으로 재실행합니다.

### PR 섹션 작성 템플릿과 검토

```markdown
제목: fix: 빈 입력 실행 오류 처리

## Why
- [확인한 문제와 영향] 빈 입력에서 예외가 발생해 사용자가 실행을 완료하지 못함
## What
- [파일·동작·전후 차이] main.py에서 빈 입력 검사 후 안내하고 종료하도록 변경
## How to Test
- [실행 명령·기대값·관측 결과] python main.py commit → 안내와 종료 코드 확인
- 미실행 항목: [대상]. 검증 제안: [명령과 기대값]
```

위 템플릿은 작성 예시이므로 실제 변경·관측 결과로 교체합니다. reason/test가 없으면 배경 미확인·테스트 미실행 표시를 유지합니다.

- 제목·What이 diff의 실제 파일과 전후 동작을 정확히 설명하는지 확인합니다.
- Why가 확인한 이유인지, 추측을 사실처럼 쓴 문장은 없는지 확인합니다.
- How to Test의 실행 명령·관측 결과·미실행 제안을 구분합니다.
- 특정 사람·팀을 근거 없이 탓하거나 편향된 표현을 사용하지 않았는지 확인합니다.
- 입력 생략/미추적/바이너리의 확인 불가 범위, 비밀값·개인정보, 잘린 제목의 의미를 확인합니다.

## 5. 안전 모드와 무료 사용  

안전 모드는 기본으로 켜집니다. status, diff, 변경 이유, 검증 설명을 전송 전에 마스킹합니다. 현재 환경변수의 키와 알려진 Gemini/GitHub/OpenAI/AWS 키 형태, 이메일, 비밀값 할당, PEM 개인키 패턴을 가립니다. `password`/`passwd`/`pwd`/`passphrase`, `api-key`/`clientSecret`/`DB_PASSWORD_2`, `비밀번호`/`암호` 같은 이름을 처리합니다. 따옴표 값·여러 줄 리터럴·YAML 블록·괄호 표현식, Authorization의 Bearer/Basic, 연결 URL의 사용자명·비밀번호도 가립니다. 길이 제한 전에 먼저 마스킹하여 잘리는 경계의 값 노출을 줄입니다.

입력은 다음 숫자로 제한합니다.  
- diff: 앞에서부터 최대 10개 `diff --git` 블록, 최대 200줄, 한 줄 최대 1,000자.  
- status/diff/reason/test: 각각 최대 20,000자. 한 항목이라도 잘리면 `omitted=true`를 전달하고 경고합니다.  
- 동일 파일이 staged/unstaged 양쪽에 있으면 두 diff 블록으로 셉니다. 고유 파일 10개를 정확히 세는 정책은 아닙니다.  

자료를 전송하기 전에 `--dry-run`으로 확인하세요. 정규표현식은 모든 비밀값이나 개인정보를 알아내지 못하며, 민감 파일을 자동으로 제외하지 않습니다. 안전 모드가 파일 전체를 안전하게 만든다고 보장하지 않습니다. `.gitignore`도 이미 추적 중인 파일은 제외하지 않습니다. 예를 들어 `.env`를 이미 추적했다면 파일을 남기는 `git rm --cached .env`로 추적을 해제하고 `.gitignore`에 추가해야 합니다. 노출된 실제 키는 폐기하고 재발급하세요.  

이 마스킹은 **AI 전송 자료와 터미널 출력**에 적용합니다. 원본 파일·Git index·커밋 이력·GitHub 파일은 수정하지 않으므로 원본을 그대로 커밋하면 비밀값도 업로드될 수 있습니다. 이름 없는 임의 문자열, 별도로 인코딩하거나 여러 표현식으로 나눈 비밀값은 알아내지 못할 수 있습니다. `--no-safe-mode`에서는 입력 원문이 전송됩니다.

정상적인 `commit`/`pr` 실행은 생성 요청을 각각 **1회만 시도**합니다. API 오류, 출력 형식 오류에도 자동 재시도나 다른 모델로의 자동 전환은 없습니다. 변경 없음/키 없음/dry-run은 0회입니다. 호출 횟수는 클라이언트의 생성 요청 시도 수이고 Google의 청구나 내부 처리를 측정한 값은 아닙니다.  

### 마스킹된 요청 JSON 확인

`python main.py pr --dry-run --temperature 0.2 --max-tokens 2048`은 실제 POST 본문을 만드는 `build_payload`를 사용해 프롬프트와 요청 JSON을 출력합니다. 안전 모드에서 입력을 먼저 마스킹하며 인증 키 헤더는 출력하지 않습니다. [CLI 실행에서 추출한 요청 JSON](docs/evidence/mock/request.json)은 실제 요청과 같은 구조의 **미전송 기록**입니다. 실제 전송 성공 여부는 별도의 live 생성 로그로 확인해야 합니다.

```json
{
  "contents": [{"role": "user", "parts": [{"text": "프롬프트와 마스킹된 자료 JSON (이 예시에서는 축약)"}]}],
  "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048, "responseMimeType": "application/json"}
}
```

실제 입력 자료의 이메일·키는 `[REDACTED]` 또는 `[REDACTED_KEY]`로 바뀝니다. 위 축약 예시는 전송 증거가 아니며 전체 프롬프트는 링크된 JSON에서 볼 수 있습니다.

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

오류 해결 명령 예시:

```powershell
# 키 미설정: 현재 프로세스에서 설정 후 실행 (실제 키가 있는 화면은 제출하지 않음)
$env:GEMINI_API_KEY = "발급받은_키"
python main.py commit
# Git 위치/변경 확인
git rev-parse --show-toplevel
git status --short --branch
# 연결 확인 후 타임아웃을 늘려 수동 실행
Test-NetConnection generativelanguage.googleapis.com -Port 443
python main.py pr --timeout 120
# MAX_TOKENS: 미완료 JSON을 쓰지 말고 예산을 늘려 수동 실행
python main.py pr --max-tokens 4096
```

HTTP 400은 서버 상세 메시지와 CLI 범위를 확인하고, 401/403은 AI Studio에서 키·권한·프로젝트·지원 지역을 확인합니다. HTTP 404는 사용 가능한 모델 이름으로 `--model`을 바꿉니다. HTTP 429는 AI Studio에서 할당량과 속도 제한을 확인하고 재시도 가능 시각 이후 수동 실행합니다. 5xx는 서비스 상태를 확인한 뒤 재실행합니다. JSON 오류/안전 필터 차단은 `--dry-run`으로 입력 누락·잘림·문제 내용을 확인합니다. 자동 재시도는 없습니다.

## 7. 요구사항 대응표  

| 요구사항 | 구현 파일·함수 | 확인 방법 | 확인 결과 |  
| --- | --- | --- | --- |
| Python 3.10 이상 터미널 CLI | `main.py: parse_args/main` | help·컴파일·임시 저장소 실행 | Python 3.12.14 및 Windows/Python 3.14.4 기본 동작 통과, 3.10 직접 실행은 미확인 |  
| Git 루트 실행 | `git_tools.py: collect_changes` | 비Git/하위 디렉터리에서 실행 | 거부 확인 |  
| status 변경 목록/diff 수집 | `collect_changes/run_git` | 실제 임시 Git 저장소 | 신규·수정·staged+unstaged·rename·빈 파일·binary 확인 |  
| 변경 없을 때 종료 | `main` | 빈 저장소에서 키 없이 실행 | 메시지 출력, 요청 0회 |  
| 환경변수 키 사용 | `main` | 키 미설정/모의 환경변수 | 누락 안내, 코드에 실제 키 없음 |  
| AI API 요청과 출력 | `gemini_api.py: generate`, `main` | 실제 Gemini 및 모의 REST로 CLI 끝까지 실행 | [실제 commit/pr 성공](docs/evidence/live/README.md), 각 요청 1회 |
| 모델/temperature/max_tokens 옵션 | `parse_args`, `generate` | 범위 오류·POST JSON 검사 | 기본값/전달/경계 확인 |  
| API 실패 원인 안내 | `generate/main` | HTTP 400/401/403/404/429/500·연결 오류 모의 | 원인 안내, 키 마스킹 확인 |  
| 커밋 제목 1줄·본문 불릿 | `build_prompt/format_draft` | 모의 생성/길이 초과 출력 | 최대 72자·권장 경고·불릿 2개 확인 |  
| PR 제목·Why/What/How to Test | `format_draft/get_items` | 누락·잘못된 타입을 가진 출력 | 최대 80자·3개 헤더·각 불릿 보충 확인 |  
| 구획을 나눈 최종 출력 | `main` | 모의 CLI 출력 | 변경 요약/초안 구분 확인 |  
| 실행당 요청 1~2회 이하 | `generate/main` | 요청 호출 수 계측 | 정상/실패 1회; 재시도 없음 |  
| 안전 모드 제공 | `safety.py: mask_sensitive/prepare_input` | 키/이메일/PEM/200줄/10블록/장문 | 마스킹과 제한 확인 |  
| README 필수 안내 | 이 문서 | 문서 검토 | 설치·키·명령·예시·한도·보안 안내 작성 |  
| GitHub 소스 push | 기능별 브랜치와 `main` 병합 | 원격 파일·커밋·브랜치 확인 | [공개 저장소](https://github.com/CMS-SUDO7/CODY-B6-2) |


## 커밋과 PR 초안을 함께 생성하는 순서  

1. 파일을 수정하고 git add로 변경을 준비합니다.  
2. python main.py commit으로 커밋 메시지를 생성합니다.  
3. python main.py pr로 PR 초안을 생성합니다.  
4. 두 결과를 검토하고 복사한 뒤 실제 커밋을 진행합니다.
