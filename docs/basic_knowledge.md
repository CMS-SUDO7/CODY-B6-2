# B6-2 기초와 핵심 지식

2026-10-16 기준으로 현재 파일 구조와 소스에 맞췄습니다. 파일별 원본 코드와 줄 번호는 [코드 흐름과 줄별 해설](code_translation.md), 실행·검증 방법은 [README](../README.md)를 참고하세요.

이 문서는 이번 코드를 읽고 수정하는 데 필요한 내용만 설명합니다. 먼저 **Git의 세 저장 위치, JSON 왕복, AI 출력 후처리** 세 가지를 이해하면 전체 흐름을 따라가기 쉽습니다.

## 1. 먼저 알아야 할 기초

### 함수, 인자, 반환값

함수는 이름을 붙여 재사용하는 작업입니다. `one_line("a\nb")`는 줄바꿈이 있는 문자열을 인자로 받고 `"a b"`를 반환합니다. 함수 내부에서 `print`를 쓰지 않으므로 이것만 호출하면 화면 출력은 없습니다. `main.py`가 반환값을 받아 `print`로 보여 줍니다.

`def generate(...) -> dict:`의 `-> dict`는 반환값이 딕셔너리라는 타입 힌트입니다. 설명과 도구 지원에 쓰이며, Python이 이 표시만 보고 자료형을 강제로 제한하지는 않습니다. 그래서 실제 응답에 `isinstance` 검사도 사용합니다.

여러 값은 튜플로 돌려줍니다. `status, diff, count, untracked = collect_changes()`는 반환된 네 값을 각각 변수에 담는 **언패킹**입니다. 순서를 바꾸면 의미가 달라집니다.

### 문자열, 리스트, 딕셔너리

- 문자열: `"fix: 출력 수정"`. 변경 설명과 API 응답 텍스트입니다.
- 리스트: `["출력 변경", "문서 보완"]`. 순서가 있는 여러 항목입니다.
- 딕셔너리: `{"title": "fix: 출력 수정"}`. 이름으로 값을 찾습니다.

`draft.get("title")`은 키가 없으면 기본값 `None`을 돌려줍니다. `draft["title"]`은 키가 없으면 `KeyError`가 발생합니다. `output_format.py`는 AI가 키를 빠뜨릴 수 있으므로 `.get()`을 사용합니다.

`len(title)`은 Python 문자열의 코드 포인트 개수를 셉니다. 일반 한글 글자 한 개는 보통 1입니다. 결합 문자나 이모지는 화면상 한 글자가 여러 코드 포인트일 수 있으며 바이트 길이와 다릅니다.

### 조건문, 반복문, 슬라이스

`if count == 0:`은 변경 수가 0일 때만 아래 코드를 실행합니다. `for notice in notices:`는 경고 목록을 순서대로 읽습니다. `while index < len(records):`는 처리할 Git 상태 항목이 남아 있는 동안 반복합니다.

`record[:2]`는 처음 두 문자입니다. `"MM app.py"`라면 `"MM"`을 가져옵니다. `title[:limit - 1]`은 제목의 앞부분만 남겨 마지막에 생략기호 한 자를 붙일 공간을 만듭니다. `items[:2]`는 불릿 항목을 최대 두 개만 남깁니다.

`" ".join(value.split())`은 공백으로 문자열을 쪼갠 뒤 한 칸으로 다시 합칩니다. 예를 들어 `"a\n  b"`가 `"a b"`가 됩니다. 이 방법으로 제목 한 줄을 만듭니다.

복잡한 조건에는 결과의 뜻을 이름으로 붙입니다. `safety.py`의 `is_numeric_output_budget`는 숫자로 된 출력 예산이라 가리지 않을 값인지, `is_yaml_block_start`는 YAML 블록으로 처리할 시작 형태인지를 나타냅니다. 이 값들은 각 할당을 처리하는 중 필요한 지점에서 계산하며, 인용 값·괄호 값 처리가 YAML 처리보다 먼저 적용됩니다. `diff_block_count`는 고유 파일 수가 아닌 diff 블록 수입니다.

### f-string과 삼항 표현식

`f"변경 {count}개"`는 변수 값을 문자열에 넣습니다. `limit = MAX_COMMIT_TITLE_CHARS if command == "commit" else MAX_PR_TITLE_CHARS`는 다음과 같습니다. 두 상수의 값은 각각 72와 80입니다.

```python
if command == "commit":
    limit = MAX_COMMIT_TITLE_CHARS
else:
    limit = MAX_PR_TITLE_CHARS
```

`main.py`의 `label` 선택도 같은 문법입니다. `items or [fallback]`은 items가 비었을 때 안내 한 항목을 대신 반환합니다.

CLI 입력 범위는 `MIN_TEMPERATURE`/`MAX_TEMPERATURE`, `MIN_OUTPUT_TOKENS`/`MAX_OUTPUT_TOKENS`, `MAX_TIMEOUT_SECONDS`로 관리합니다. 검증 조건과 오류 안내가 같은 상수를 사용하므로 범위를 바꿀 때 두 곳의 숫자를 따로 수정하지 않습니다. 현재 허용 범위와 기본값은 그대로입니다.

### 예외와 종료 코드

예외는 정상 처리할 수 없는 상황을 전달하는 방식입니다. `run_git()`은 Git 실패를 `ValueError`로 바꾸고 `main()`이 잡아 안내합니다. `raise ... from error`는 새 오류와 원래 오류의 관계를 남깁니다.

`try`는 실패할 수 있는 작업, `except`는 실패 처리, `finally`는 성공·실패·중간 `return`과 관계없이 실행할 마무리입니다. 이 프로젝트에서는 `finally`가 `api_request_attempts`에 기록한 API 요청 시도 횟수를 출력합니다. 요청이 실패해도 시도했다면 1이며 성공 횟수나 청구 횟수가 아닙니다. CLI 인자 해석은 try 이전이므로 `--help`나 사용법 오류에는 이 로그가 없습니다.

`sys.exit(main())`은 main의 숫자를 운영체제에 반환합니다. 0은 정상, 1은 실행 오류, 2는 CLI 사용법 오류, 130은 사용자 중단입니다.

### 모듈과 실행 위치

모듈은 Python 파일입니다. 현재 프로젝트는 6개 모듈로 나뉩니다.

| 파일 | 맡은 일 | 먼저 볼 함수 |
| --- | --- | --- |
| [main.py](../main.py) | 전체 흐름과 터미널 출력 | main |
| [cli.py](../cli.py) | 옵션 해석·범위 검증 | parse_args |
| [git_changes.py](../git_changes.py) | 저장소 루트·상태·diff 확인 | collect_changes, run_git |
| [safety.py](../safety.py) | 비밀값 마스킹·입력 크기 제한 | mask_sensitive, prepare_input |
| [gemini_api.py](../gemini_api.py) | 프롬프트·요청 본문·응답·오류 처리 | build_prompt, build_payload, generate |
| [output_format.py](../output_format.py) | 제목·불릿·PR 섹션 보정 | one_line, get_items, format_draft |

Git 수집과 형식 보정을 API 없이 따로 확인할 수 있도록 분리했습니다. docs에는 이 두 학습 문서, 초기 검증 기록인 verification.md, 미션 PDF가 있습니다. 현재 실행·검증 예제와 실제 Gemini 실행 기록은 README에 모았습니다. 별도 테스트 폴더나 패키지 설치 파일은 없으며, Python 3.10 이상과 Git을 사용합니다. Python 표준 라이브러리만 사용하므로 pip 설치는 필요하지 않습니다.

`if __name__ == "__main__":`은 파일을 직접 실행한 경우만 main을 부릅니다. 다른 파일이 `import main`하면 프로그램이 자동 실행되지 않습니다.

현재 작업 디렉터리와 소스 파일 위치는 다를 수 있습니다. `python C:\tools\main.py pr`를 mini-redis 루트에서 실행하면 Git 대상은 mini-redis입니다. `Path.cwd()`는 현재 실행 폴더를 가져옵니다.

### 환경변수와 외부 명령

환경변수는 실행 중인 프로그램이 읽을 수 있는 이름·값입니다. PowerShell의 `$env:GEMINI_API_KEY`가 `os.environ.get("GEMINI_API_KEY", "")`로 들어갑니다. 코드 파일의 변수와 다르고 `.env`라는 파일도 자동으로 같은 역할을 하지 않습니다.

`subprocess.run(["git", "diff"], ...)`는 Python 밖의 Git 프로그램을 실행합니다. 문자열을 셸에서 해석하지 않고 인자 목록으로 전달합니다. `*arguments`는 리스트 항목을 바깥 리스트에 펼칩니다. `capture_output=True`로 받은 출력은 `result.stdout`, 오류는 `result.stderr`에서 읽습니다.

### 정규표현식, 위치, 스택

`re.compile()`은 반복 사용할 패턴을 준비하고, `finditer()`는 일치한 위치를 하나씩 제공합니다. `match.start()`와 `match.end()`는 각각 일치 구간의 시작과 끝 다음 위치입니다. `(?P<name>...)`은 이름을 붙인 캡처 그룹이며 `match.group("name")`으로 읽습니다. `re.IGNORECASE`는 대소문자를 구별하지 않습니다.

`safety.py`의 `cursor`는 이미 결과에 반영한 원문의 끝을 기억합니다. 원문 조각과 `[REDACTED]`를 `pieces`에 모은 다음 `"".join(pieces)`로 연결합니다. 이미 가린 여러 줄 값 안에서 다시 발견한 할당은 건너뜁니다.

스택은 마지막에 넣은 값을 먼저 꺼내는 구조입니다. `_compound_end()`는 여는 괄호를 만나면 대응하는 닫는 괄호를 `append`하고, 맞는 닫는 괄호를 만나면 `pop`합니다. 예를 들어 `{"items": [1, 2]}`는 `}`를 기다리다가 그 안에서 `]`도 기다립니다. 따옴표 안의 괄호는 `_quoted_end()`로 문자열 끝까지 건너뛰어 구조로 세지 않습니다. 코드의 밑줄로 시작하는 함수 이름은 내부 보조 함수라는 관례이지 접근을 강제하는 문법은 아닙니다.

## 2. 미션에서 사용하는 용어

| 용어 | 쉬운 정의와 예시 | 이 코드와의 연결 |
| --- | --- | --- |
| CLI: Command Line Interface | 터미널 명령으로 조작하는 프로그램 | `python main.py pr`와 `argparse` |
| 저장소(repository) | Git이 변경을 관리하는 프로젝트 | `collect_changes`가 루트 확인 |
| 작업 폴더(working tree) | 지금 편집 중인 실제 파일 | `git diff`가 unstaged 변경 확인 |
| 인덱스(index)/staging area | 다음 커밋에 넣으려고 선택한 상태 | `git add`, `git diff --cached` |
| 커밋(commit) | 저장소에 기록하는 변경 스냅샷 | 도구는 메시지만 만들고 커밋하지 않음 |
| diff | 변경 전후의 차이; `-`는 제거, `+`는 추가 | `git_changes.py`가 입력 수집 |
| untracked(미추적) | Git이 아직 추적하지 않는 새 파일 | status `??`, diff에는 내용 없음 |
| PR: Pull Request | 브랜치 변경을 검토하고 합치도록 요청 | 이번 도구는 제목과 본문 텍스트만 출력 |
| API: Application Programming Interface | 다른 프로그램에 작업을 요청하는 약속 | `generate`가 Gemini에 요청 |
| REST API | URL과 HTTP 요청으로 자원을 다루는 인터페이스 방식 | generateContent 주소에 POST |
| HTTP: Hypertext Transfer Protocol | 클라이언트와 서버의 요청·응답 규칙 | Request와 urlopen |
| HTTPS | TLS로 통신 구간을 암호화하는 HTTP | Gemini의 https 주소 |
| POST | 요청 본문을 서버에 보내는 HTTP 메서드 | 프롬프트 JSON을 전송 |
| header(헤더) | 요청의 형식·인증 등 부가 정보 | Content-Type, x-goog-api-key |
| body(본문) | 전송할 실제 자료 | payload를 JSON 바이트로 전송 |
| JSON: JavaScript Object Notation | 문자열·숫자·배열·객체를 표현하는 교환 형식 | json.dumps와 json.loads |
| UTF-8 | 한글 등을 바이트로 바꾸는 문자 인코딩 | encode/decode |
| 프롬프트(prompt) | AI가 수행할 작업과 자료를 담은 입력 | build_prompt |
| 컨텍스트(context) | 변경을 이해하는 데 필요한 맥락 | status/diff/reason/test |
| 토큰(token) | 모델이 읽고 생성하는 텍스트 단위 | maxOutputTokens; 글자 수와 다름 |
| temperature | 다음 토큰 선택의 다양성 조절값 | CLI 값을 generationConfig에 전달 |
| 마스킹(masking) | 원래 값을 가림 문자열로 치환 | 이메일 → [REDACTED] |
| 정규표현식(regex) | 문자열 패턴을 찾는 문법 | re.sub로 키 형태 검색·치환 |
| quota/할당량 | 프로젝트가 사용할 수 있는 요청·토큰 한도 | 429 안내, 자동 재시도 없음 |
| timeout | 네트워크 작업을 기다리는 시간 제한 | generate의 timeout 인자 |
| 후처리 | AI 결과를 받은 뒤 프로그램에서 정리 | format_draft가 헤더·길이 보정 |
| 모의 응답(mock) | 실제 서버 대신 준비한 응답 | 키 없이 요청 구성·오류 흐름 검증 |

`HTTP 200`은 요청 성공 상태지만 AI 문구의 사실성까지 보장하지 않습니다. `401/403`은 인증·권한 관련 확인, `404`는 모델/주소 확인, `429`는 한도 확인, `5xx`는 서버 측 상태 확인의 출발점이며 실제 응답의 오류 내용을 함께 읽습니다.

## 3. 이번 미션의 핵심

### 핵심 1: Git 세 위치를 구분한다

작업 폴더는 현재 편집본, 인덱스는 커밋할 선택본, HEAD는 보통 현재 커밋입니다. 최초 커밋 전에는 HEAD 커밋이 없지만 `git diff --cached`는 인덱스에 추가된 파일을 보여 줍니다.

`app.py`가 HEAD에서 `print(1)`, 인덱스에서 `print(2)`, 작업 폴더에서 `print(3)`이라고 합시다.

| 명령 | 비교 | 대표 변경 |
| --- | --- | --- |
| `git status --porcelain=v1 -z` | 변경 상태 표시 | `MM app.py` |
| `git diff --cached` | HEAD → 인덱스 | 1 → 2 |
| `git diff` | 인덱스 → 작업 폴더 | 2 → 3 |

`collect_changes()`는 두 diff를 `[STAGED]`와 `[UNSTAGED]`로 나누어 함께 전달합니다. `commit`과 `pr` 모두 같은 수집 범위를 사용합니다. 일반적인 `git commit`이 기록하는 것은 인덱스이므로 초안을 실제 커밋에 적용할 때는 인덱스와 범위를 대조해야 합니다.

예를 들어 README만 스테이징하고 Python 수정은 작업 폴더에 남겨 두면, 커밋 초안에도 Python 변경이 들어갈 수 있습니다. 현재 CLI에는 staged만 선택하는 옵션이 없습니다. `git diff --cached`로 실제 커밋 범위를 확인하고, 초안에서 그 범위 밖의 설명을 수정합니다. `pr`도 브랜치에 이미 커밋된 변경 전체를 비교하지 않으므로, 커밋 뒤 작업 트리가 깨끗하면 변경 없음으로 종료합니다.

미추적 파일은 status에 경로만 있고 diff에 본문이 없습니다. 바이너리 변경도 이 도구가 파일 본문을 해석하지 않습니다. `--test`는 실제로 수행한 검증을 설명하는 문자열이며 테스트를 실행하는 옵션이 아닙니다.

status의 앞 두 문자는 상태 코드입니다. 첫 문자는 인덱스, 둘째는 작업 폴더 상태입니다. `" M"`은 unstaged 수정, `"M "`은 staged 수정, `"??"`는 미추적입니다. `-z`는 항목을 NUL(`\0`) 문자로 구분합니다. rename/copy는 새 경로와 원래 경로가 별도 항목이므로 `index`를 한 번 더 증가시킵니다.

루트 확인에는 `rev-parse --show-toplevel`만 보조로 사용합니다. 변경 데이터는 status와 diff에서만 읽고 log, show, 커밋 간 비교는 사용하지 않습니다. 텍스트 변환기·외부 diff·ANSI 색상을 끄므로 diff 자료에 불필요한 실행이나 장식이 섞이는 것을 줄입니다.

### 핵심 2: JSON을 두 번 해석한다

Python 딕셔너리는 그대로 HTTP 전송할 수 없으므로 다음 변환이 필요합니다.

1. `build_payload()`가 만든 `payload` 딕셔너리 → `json.dumps` 문자열 → `encode("utf-8")` 바이트.
2. POST 응답 바이트 → `decode("utf-8")` 문자열 → `json.loads` 딕셔너리.
3. 응답의 candidate 안에서 텍스트를 모음 → 다시 `json.loads` → AI 초안 딕셔너리.

2번은 서버 응답 봉투를 열고, 3번은 봉투 안의 AI 초안을 읽는 작업입니다. 실제 대응은 `result`와 `draft`입니다. `responseMimeType="application/json"`으로 AI의 JSON 출력을 요청하지만 유효성과 형태를 다시 확인합니다.

`build_payload()`는 `contents`에 프롬프트를, `generationConfig`에 temperature·maxOutputTokens·responseMimeType을 넣습니다. `generate()`와 `--dry-run`이 같은 함수를 사용하므로 전송할 본문과 미리보기 구조가 같습니다. 인증 키는 본문 대신 `x-goog-api-key` HTTP 헤더에 넣으며 dry-run은 그 헤더를 출력하지 않습니다. 변경이 있는 저장소에서 dry-run을 실행하면 프롬프트와 요청 JSON을 보여 주고 API 호출은 0회입니다. 키가 없어도 실행할 수 있습니다.

`finishReason="STOP"`일 때만 완료로 처리합니다. `MAX_TOKENS`라면 JSON 중간에 끊겼을 수 있으므로 결과를 성공처럼 출력하지 않습니다. `thought=true`인 사고 내용은 최종 초안 텍스트에 합치지 않습니다.

HTTP 오류는 상태 코드와 서버 본문을 함께 읽습니다. `_is_invalid_api_key()`는 `error.details`의 비어 있지 않은 reason 중 `API_KEY_INVALID`가 있는지 우선 확인합니다. 명시적인 reason이 없을 때만 오류 메시지의 특정 접두사로 보조 판단합니다. 따라서 400이나 403이라는 숫자만으로 잘못된 키라고 단정하지 않습니다. 원문으로 원인을 판별한 다음, 오류 본문을 마스킹하고 앞 500자만 안내에 사용합니다. 실패해도 자동 재시도는 없습니다.

상세 오류는 반복문으로 하나씩 읽습니다. 딕셔너리가 아닌 항목은 `continue`로 건너뛰고, `reason`이 비어 있지 않은 문자열인 경우에만 목록에 추가합니다. 여러 검사를 긴 리스트 내포에 몰아넣지 않아 어떤 항목이 제외되는지 순서대로 확인할 수 있습니다.

### 핵심 3: 프롬프트와 후처리의 책임을 나눈다

`build_prompt()`는 한국어, prefix, 길이, 데이터에 근거한 요약, 변경 배경과 테스트 사실의 구분을 요청합니다. `reason`이 비면 이유를 추측하는 대신 미확인이라고 쓰게 합니다. `test`를 생략하면 성공했다고 쓰지 않도록 지시합니다. 이 규칙은 AI의 사실성을 강제로 보장하지 않으므로 사람이 검토합니다.

`format_draft()`는 프로그램이 확실하게 다룰 수 있는 형식을 처리합니다. 제목에서 줄바꿈 제거, 최대 길이 적용, 불릿 생성, 세 PR 헤더 생성이 여기의 역할입니다. 자동 재생성 대신 로컬 보정을 선택하여 실행당 요청을 1회로 제한합니다.

제목이 90자라면 커밋 모드에서 앞 71자를 남기고 뒤쪽 공백을 정리한 뒤 `…`를 붙여 최대 72자로 만들고 경고합니다. 커밋 50자는 권장 길이, 72자는 실제 상한이며 PR 제목 상한은 80자입니다. 커밋 본문은 유효한 changes 항목을 최대 2개 남기고, 없으면 제목을 이용한 안내 한 항목을 넣습니다.

빈 제목은 오류로 종료합니다. PR의 Why/What/How to Test 값이 리스트가 아니거나 정리 후 유효한 문자열 항목이 하나도 없으면 미확인·diff 확인·미실행 안내를 보충하고 경고합니다. 경고에는 필드별 작성 예시도 붙지만 그 예시를 실제 변경이나 검증 결과로 본문에 넣지는 않습니다. 잘린 문장의 의미와 자동 보충한 내용을 작성자가 확인합니다. prefix 선택은 프롬프트의 요청이며 후처리에서 prefix를 검사하거나 자동 추가하지 않습니다.

### 여러 줄 비밀값을 가리는 순서

`mask_sensitive()`는 현재 API 키와 정확히 같은 문자열을 먼저 가리고, URL의 사용자명·비밀번호, Authorization/Bearer/Basic, PEM 개인키를 처리합니다. 이어 `_mask_assignments()`로 비밀값 이름 뒤의 값을 가리고, 알려진 키 접두사와 이메일 패턴도 적용합니다. 이름 패턴에는 password/passphrase/pwd, api-key, clientSecret, DB_PASSWORD_2와 비밀번호·암호·토큰 같은 한글 이름도 포함합니다.

비밀값이 한 줄에서 끝난다고 가정하면 다음 줄의 값이 남을 수 있습니다. 현재 코드는 다음처럼 범위를 나눠 찾습니다.

| 값의 형태 | 범위를 찾는 방법 |
| --- | --- |
| 일반·삼중 따옴표, 이스케이프된 인용 값 | _quoted_end로 닫는 따옴표까지 탐색 |
| 괄호·배열·객체 | _compound_end의 스택으로 중첩된 괄호가 닫힐 때까지 탐색 |
| YAML 블록, 이름 뒤에 줄바꿈한 값 | diff의 +/-를 제외한 들여쓰기로 블록 끝 확인, 다음 줄의 따옴표·괄호도 확인 |
| 따옴표 없는 값 | 같은 줄의 나머지를 보수적으로 가림 |

닫는 따옴표나 괄호가 없으면 문자열 끝까지 가릴 수 있습니다. `max_tokens=2048`, `"maxOutputTokens": 2048`처럼 숫자로 된 출력 예산은 유지합니다. 이 예외가 모든 token 이름을 허용하는 것은 아니며, 임의 문자열·인코딩·분할 표현식은 놓칠 수 있습니다.

`prepare_input()`은 안전 모드에서 status/diff/reason/test를 **먼저 마스킹한 뒤** 길이를 제한합니다. 먼저 잘라 버리면 경계를 걸친 비밀값을 패턴으로 알아보지 못할 수 있기 때문입니다. 원본 파일을 수정하는 작업은 아닙니다.

### 입력 제한과 자료구조 선택

안전 모드의 전송 입력 상한은 다음과 같습니다.

| 대상 | 상한 | 세는 기준 |
| --- | --- | --- |
| diff 블록 | 10개 | `diff --git ` 헤더마다 1개, 같은 파일의 staged/unstaged도 별도 |
| diff 줄 | 200줄 | `[STAGED]`, `[UNSTAGED]` 구분 줄도 포함 |
| diff 한 줄 | 1,000자 | 마스킹 후 각 줄의 앞부분 |
| status/diff/reason/test | 항목별 20,000자 | diff 블록·줄 제한 뒤 마지막 문자 제한 |

어느 상한으로든 내용이 잘리면 반환값과 입력 딕셔너리의 `omitted`가 True가 됩니다. 이 값은 비밀값을 가렸다는 표시가 아니라 크기 제한에 따른 생략 표시입니다. 앞에서부터 남기므로 중요한 변경이 뒤에서 빠질 수 있고 생략 파일 수나 줄 범위는 따로 계산하지 않습니다.

`--no-safe-mode`는 전송 입력의 마스킹과 크기 제한을 모두 끕니다. dry-run도 이 경우 원문을 출력합니다. 생성 결과·일반 오류의 터미널 출력은 main에서 별도로 마스킹합니다. 마스킹이 완전한 비밀 탐지를 보장하지는 않습니다.

딕셔너리는 이름별 컨텍스트를 저장하고, 리스트는 순서가 있는 상태·텍스트 조각·불릿과 괄호 탐색 스택을 저장합니다. 별도의 트리, 힙, 연결리스트는 사용하지 않습니다.

`N`을 처리할 텍스트의 문자 수라고 하면 status 분리는 O(N)입니다. diff 제한 루프는 최대 200줄을 담고, 더 많은 줄이 있으면 다음 반복에서 종료합니다. 다만 `splitlines()`는 전체 diff의 목록을 먼저 만들므로 시간·추가 공간이 O(N)입니다. `join`도 합칠 전체 문자 수만큼 작업합니다.

현재 마스킹은 고정된 네 정규식 외에 할당 이름 검색, 인용 값·괄호 탐색, YAML 들여쓰기 처리를 포함합니다. 문자열 뒤쪽을 슬라이스하거나 `splitlines()`하는 작업이 여러 할당에서 반복될 수 있으므로 전체 마스킹을 항상 O(N)이라고 설명할 수는 없습니다. 정규표현식과 입력 형태에 따라 비용이 달라집니다. 괄호 탐색 스택의 크기는 중첩 깊이에 따라 증가합니다.

마스킹과 제한은 **전송량**을 줄이며 Git 출력의 로컬 메모리 수집량을 제한하지 않습니다. `subprocess.run(capture_output=True)`는 전체 출력을 메모리에 받습니다. Git 자체의 diff 계산 비용, AI 서버 추론 시간, 네트워크 지연은 위 Python 루프 비용 분석에 포함하지 않습니다. 입력이 매우 큰 실제 서비스에서는 스트리밍이나 파일별 수집이 별도로 필요합니다.

### 파라미터를 바꿔 보는 이유

`--temperature 1.0`은 기본값입니다. 더 낮은 값은 표현 다양성을 줄이는 데 사용할 수 있지만 모델에 따라 영향이 달라질 수 있고 낮추면 언제나 더 정확해지는 것은 아닙니다. 같은 입력이라도 문구가 달라질 수 있습니다. 모델에 맞는 권장값은 공식 문서를 확인합니다.

`--max-tokens 2048`은 생성 토큰의 상한이지 2,048글자를 보장하는 값이 아닙니다. 모델의 thinking 사용량도 예산에 영향을 줄 수 있습니다. 너무 작은 값으로 JSON이 끊기면 `MAX_TOKENS` 오류를 확인하고 수동으로 늘립니다.

### 학습용 구현과 실제 서비스의 차이

이 도구는 동기식입니다. 한 요청의 응답을 기다리는 동안 다음 작업을 하지 않습니다. 대규모 비동기 작업, 재시도 큐, 사용자별 권한, 사용량 저장, 로그 관리, 완전한 비밀 탐지는 구현하지 않았습니다. 제한된 정규표현식은 미탐지·과도한 가림이 모두 가능하고 안전 모드는 보안 검증이 아닙니다. AI 초안은 자동 커밋·자동 PR 게시에 사용하지 않습니다.

## 4. 나중에 공부할 확장 지식

- JSON Schema: 출력 항목의 자료형을 API 요청 단계에서 지정하는 방법. 이번 코드는 JSON MIME과 로컬 검증을 사용합니다.
- 요청 제한과 backoff: 일정 시간을 늘려 재시도하는 정책. 지금은 자동 재시도가 없어 실행당 1회입니다.
- `asyncio`와 비동기 HTTP: 여러 요청을 기다리는 동안 다른 일을 하는 방법. 현재 단일 CLI에는 필수가 아닙니다.
- 변경 범위 선택: commit에서 staged만 선택하는 옵션과, PR에 포함된 커밋 전체를 `merge-base`·base/head 비교로 수집하는 방식. 둘 다 현재는 구현하지 않았습니다.
- 파일별 제외 정책과 전문 비밀 탐지: 정규표현식만으로 놓치는 민감정보를 줄이는 방법.

## 5. 작은 학습 과제

### 문제 1: 출력 예상

`output_format.py`의 `format_draft()`에 다음을 넘기면 제목은 몇 자이며 경고는 몇 개인가요?

```python
format_draft("commit", {"title": "a" * 90, "changes": ["출력 수정"]})
```

### 문제 2: 값의 변화 추적

`git_changes.py: collect_changes()`에서 `records`가 다음과 같다고 가정합니다. 첫 번째 루프와 두 번째 루프가 끝난 뒤 `index`, `statuses`, `untracked`를 써 보세요.

```python
["R  new.py", "old.py", "?? memo.txt", ""]
```

### 문제 3: 작은 기능 수정

`safety.py`의 `MAX_DIFF_LINES`를 200에서 100으로 바꾸세요. 다른 제한에 걸리지 않는 짧은 150줄 샘플 diff에서 반환된 줄 수는 100이고 `omitted`는 True여야 합니다. README와 이 기초 문서, 줄별 해설의 숫자·줄 번호도 함께 맞춥니다. 이는 학습 과제이며 현재 실제 상한은 200줄입니다.

### 문제 4: 여러 줄 마스킹과 생략 표시

다음은 실제 비밀값이 아닌 학습용 문자열입니다. 결과에 가짜 값이 남는지, 출력 예산이 유지되는지, omitted가 True인지 예상해 보세요.

```python
sample = 'password = (\n    "demo-part-one"\n    "demo-part-two"\n)\nmax_tokens=2048'
data, omitted = prepare_input("M config.py", sample, "", "", True, "")
```

### 힌트와 해설

1. 71자의 `a`와 `…`가 합쳐져 72자입니다. 최대 길이 보정 경고와 50자 권장 경고가 생겨 총 2개입니다.
2. 첫 번째 항목을 읽어 index가 1이 된 뒤 이름 변경의 원래 경로도 소비해 2가 됩니다. statuses는 `["R  new.py <- old.py"]`, untracked는 0입니다. 다음 루프는 memo를 읽어 index 3, statuses에 `"?? memo.txt"` 추가, untracked 1입니다. 끝의 빈 항목은 다음 루프에서 건너뜁니다.
3. `MAX_DIFF_LINES = 200`의 200을 100으로 바꿉니다. `prepare_input()`은 이 상수를 읽으므로 조건문을 따로 수정하지 않습니다. 다른 제한에 걸리지 않는 입력은 100줄까지 append한 뒤 다음 줄에서 omitted를 True로 설정하고 break합니다. 정확히 100줄이고 다른 상한에도 걸리지 않으면 생략이 없어 False입니다.
4. 두 demo 문자열은 괄호 표현식 전체와 함께 `[REDACTED]`로 바뀌고 `max_tokens=2048`은 유지됩니다. 이 작은 입력은 크기 제한에 걸리지 않으므로 omitted는 False입니다. 마스킹과 입력 생략은 다른 작업입니다.

## 6. 추천 책 한 권

**《파이썬 코딩 도장 개정증보판》 — 남재윤, 길벗.**

함수, 문자열, 딕셔너리, 모듈, 예외, 정규표현식을 다시 확인하는 참고서로 추천합니다. 이번 미션은 새로운 문법 자체보다 문법을 Git과 HTTP에 연결하는 과제이므로, 필요한 단원을 읽고 같은 코드를 직접 고치는 방법이 맞습니다. 최신 Gemini 모델과 REST 사양은 책 대신 공식 문서를 사용하세요.

추천 순서: 문자열 → 리스트/딕셔너리 → 함수 → 모듈 → 예외 처리 → 정규표현식. 해당 주제를 이 프로젝트의 one_line/get_items/run_git/generate/mask_sensitive와 연결해서 읽습니다.

[출판사 도서·목차 안내](https://cafe.gilbut.co.kr/book/view?bookcode=BN003634)에서 저자와 개정증보판 정보를 확인했습니다. 가격이나 구매를 전제로 하지 않으며 같은 책을 이미 갖고 있다면 추가 책을 살 필요 없습니다.
