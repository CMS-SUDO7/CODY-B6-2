# 코드로 따라가는 Git 변경 설명 도우미

이 문서는 Python을 처음 배우는 사람이 프로그램의 **기능과 데이터 흐름**을 이해하도록 쓴 해설입니다. 코드를 한 줄씩 번역하는 대신, 함께 작동하는 함수를 묶어 설명합니다. 실행 방법은 [README](../README.md)에 있습니다.

읽을 때는 터미널 명령 하나를 머릿속에 두면 좋습니다.

```bash
python3 main.py commit --safe-mode --staged --files main.py --reason "CLI 오류 안내 개선"
```

이 명령의 목표는 `main.py`의 **스테이징된 변경**을 AI에게 설명하고 커밋 메시지 초안을 출력하는 것입니다. 실제 변경이 없거나 API 키가 없다면 해당 단계에서 멈춥니다.

## 먼저 알아둘 말

| 말 | 이 프로젝트에서 뜻하는 것 |
| --- | --- |
| CLI | 터미널에서 명령과 옵션을 입력해 실행하는 프로그램 |
| 작업 파일 | 지금 폴더에서 편집 중인 파일 |
| 스테이징 영역 | `git add`로 다음 커밋에 넣겠다고 선택한 파일 내용 |
| diff | 기존 내용과 바뀐 내용을 보여 주는 Git의 비교 결과 |
| 문맥(context) | AI에게 보내는 명령 종류, Git 상태, diff, 변경 이유 등의 묶음 |
| 초안(draft) | AI가 만든 텍스트를 제목·본문·PR 섹션으로 해석한 결과 |

프로그램이 다루는 데이터는 다음처럼 변합니다.

```text
터미널 인수
  → args: 사용자가 선택한 옵션
  → status, diff: Git에서 읽은 변경
  → context: 마스킹한 변경과 작성 지침에 필요한 정보
  → payload: API에 보낼 JSON 요청
  → text: API 응답에서 꺼낸 AI의 글
  → draft: 제목과 본문으로 나눈 자료
  → output: 화면에 보여 줄 커밋 메시지 또는 PR 초안
```

## 파일 네 개는 어떻게 나뉘나요?

| 파일 | 핵심 함수 | 역할 |
| --- | --- | --- |
| `main.py` | `parse_args`, `main` | 입력 검사부터 출력까지 전체 순서를 관리 |
| `git_context.py` | `collect_changes`, `mask_text`, `limit_diff` | Git 변경을 읽고 전송 전에 보호·제한 |
| `ai_client.py` | `build_payload`, `request_text` | 프롬프트와 HTTP 요청을 만들고 응답을 해석 |
| `formatting.py` | `parse_draft`, `render_draft` | AI 글을 커밋/PR 양식으로 정리 |

`main.py`를 중심으로 나머지 세 파일이 필요한 일을 나눠 맡습니다. 아래 순서대로 읽으면 실제 실행 순서와 거의 같습니다.

## 1. `main.py`: 명령과 옵션을 해석하기

`parse_args()`는 Python 표준 라이브러리 `argparse`를 사용합니다. **위치 인수** `command`에는 `commit` 또는 `pr` 중 하나가 반드시 들어가야 합니다. `--staged`처럼 값을 받지 않는 옵션은 `action='store_true'`이므로 쓰면 `True`, 생략하면 `False`입니다.

```python
parser.add_argument('command', choices=['commit', 'pr'])
parser.add_argument('--staged', action='store_true')
parser.add_argument('--files', nargs='+', default=[])
args = parser.parse_args()
```

`--files main.py ai_client.py`라고 쓰면 `args.files`는 파일 이름 두 개가 든 리스트가 됩니다. 아무 파일도 지정하지 않으면 빈 리스트이며, 뒤에서 Git diff 전체를 조회합니다. `--reason`은 사용자가 알고 있는 변경 이유, `--convention`은 팀의 표현 규칙을 AI 입력에 더합니다. 코드를 읽어도 알 수 없는 배경을 AI가 추측하지 않게 하는 용도입니다.

옵션의 범위도 여기서 검사합니다. 예를 들어 temperature는 지정했다면 0~2여야 하고, `--max-lines`는 5 이상이어야 합니다. 잘못된 값이면 `parser.error()`가 사용법을 보여 주고 종료 코드 2로 끝냅니다. 아직 Git 조회나 API 호출은 시작되지 않았습니다.

### 초보자가 볼 포인트

`args`는 `Namespace` 객체입니다. `args.command`, `args.staged`처럼 점(`.`)으로 각 옵션을 읽습니다. 이 값들이 이후 함수에 전달되며 프로그램의 동작을 결정합니다.

## 2. `git_context.py`: Git에서 변경 읽기

`main()`은 먼저 아래처럼 Git 정보를 받습니다.

```python
status, diff = collect_changes(args.staged, args.files)
```

Python은 함수가 반환한 두 값을 왼쪽 변수 두 개에 나누어 담을 수 있습니다. 여기서 `status`는 어떤 파일이 바뀌었는지 보여 주는 문자열이고, `diff`는 바뀐 내용이 담긴 문자열입니다.

`collect_changes()`는 Git 루트에 `.git`이 있는지 확인한 뒤 `run_git()`을 통해 Git 명령을 실행합니다. `run_git()`은 `subprocess.run(['git', ...])` 형태로 **인수 목록**을 넘깁니다. 터미널 명령 전체를 문자열로 만들어 셸에 해석시키지 않습니다. 실행 결과의 `stdout`을 문자열로 받고, Git 실패나 15초 초과는 사용자가 이해할 수 있는 오류로 바꿉니다.

```text
git status --short --branch --untracked-files=all
git diff --cached -- ...파일 선택...
git diff -- ...파일 선택...       ← --staged가 없을 때만
```

`--cached`는 스테이징 영역을 뜻합니다. 그래서 `--staged`를 켜면 `git add`한 변경만 읽고, 끄면 스테이징된 변경과 아직 스테이징하지 않은 작업 파일 변경을 모두 읽습니다. 두 diff에는 `[STAGED]`, `[UNSTAGED]` 표식을 붙여 AI가 출처를 구별하도록 합니다. `--files`는 두 diff 조회의 파일 경로를 좁힙니다.

**주의:** `git status`의 파일 수는 저장소 전체 기준이고, `--files`는 diff에만 적용됩니다. 새 파일은 `git status`에 `??`로 나타나지만 `git add` 전에는 내용이 diff에 들어오지 않습니다. 이 경우 `main.py`가 경고를 출력합니다.

### 변경이 없을 때의 갈림길

`main()`은 상태 항목이 없으면 “변경 사항이 없습니다”를 출력하고 종료합니다. 상태는 있지만 선택한 범위의 diff가 비어 있어도 API를 호출하지 않습니다. 미해결 병합 충돌이 있으면 초안을 생성하기 전에 중단합니다. 이 세 경우의 API 호출 횟수는 0입니다.

## 3. `git_context.py`와 `main.py`: 전송할 내용 보호하기

`--safe-mode`가 켜졌을 때 `main()`은 두 함수를 차례로 호출합니다.

```python
diff = mask_text(diff)
diff, truncated = limit_diff(diff, args.max_files, args.max_lines)
```

순서가 중요합니다. `mask_text()`가 먼저 API 키와 같은 실제 값, 대표적인 키·비밀번호 할당 패턴, 이메일, 개인키 블록 등을 가립니다. 여러 줄에 걸친 개인키를 **diff를 자르기 전에** 찾아야 한 부분만 남는 일을 줄일 수 있습니다. 다만 정규식으로 모든 민감정보를 찾을 수는 없습니다.

`limit_diff()`는 마스킹된 diff의 앞부분을 기본 최대 10개 파일 블록·200줄까지 선택합니다. 반환값은 `(선택한 diff, 잘렸는지 여부)`라는 두 값입니다. 같은 파일이 staged와 unstaged 양쪽에 있으면 두 블록으로 셉니다. 파일 사이에 줄을 균등하게 나누지는 않으므로 마지막 파일 중간에서 잘릴 수 있습니다.

안전 모드가 꺼져도 `redact_key()`는 **현재 환경변수의 API 키와 정확히 같은 문자열**을 문맥에서 제거합니다. 안전 모드를 켜면 상태와 변경 이유, 팀 규칙에도 대표 패턴 마스킹을 적용합니다. 화면에는 수집한 diff 줄 수와 실제 전송할 줄 수를 따로 표시합니다.

### AI에게 보내는 `context`

`main.py`는 다음 이름의 값을 딕셔너리로 묶습니다.

```python
context = {
    'command': args.command,
    'status': status,
    'diff': diff,
    'reason': args.reason,
    'convention': args.convention,
    'truncated': truncated,
}
```

딕셔너리는 이름표(key)로 값을 찾는 자료형입니다. `truncated=True`라면 AI에게 일부 diff만 전달됐다는 사실도 함께 알려 줍니다. `json.dumps()`로 이 자료를 문자열로 만들고, 전체 문맥이 100,000자를 넘으면 중단합니다.

`--dry-run`은 이 지점에서 `build_payload()`가 만들 요청 본문을 화면에 보여 주고 끝납니다. 키가 없어도 실행할 수 있고 API 호출 횟수는 0입니다. 실제로 전송될 내용을 확인하는 가장 쉬운 방법입니다.

## 4. `ai_client.py`: AI에게 요청 만들기

실제 호출을 시작할 때 `main.py`는 `AI_API_KEY` 환경변수를 읽습니다. 비어 있거나 공백·ASCII 이외 문자가 포함되면 요청 전에 오류를 냅니다. 키를 코드나 문서에 하드코딩하지 않는 이유는 저장소에 비밀이 남지 않게 하기 위해서입니다.

`build_payload(args, context)`는 API에 보낼 파이썬 딕셔너리를 만듭니다.

```python
payload = {
    'model': args.model,
    'messages': [
        {'role': 'system', 'content': instruction + rule + '\n출력 양식:\n' + template},
        {'role': 'user', 'content': context},
    ],
}
```

`system` 메시지에는 “관찰한 변경만 설명”, “테스트를 실행했다고 주장하지 않기” 같은 작성 규칙과 출력 양식이 들어갑니다. `user` 메시지에는 앞에서 만든 Git 변경 문맥이 들어갑니다. `commit`이면 제목과 핵심 변경 불릿을, `pr`이면 제목과 `Why`·`What`·`How to Test` 섹션을 요구합니다. diff 안에 적힌 명령은 자료일 뿐, AI가 따라야 할 지시가 아니라는 규칙도 넣습니다.

기본 요청에는 `model`과 `messages`만 들어갑니다. `--temperature`나 `--max-tokens`를 명시하면 그때만 관련 필드를 추가합니다. `--token-parameter`는 출력 상한을 `max_completion_tokens`와 `max_tokens` 중 어느 이름으로 보낼지 정합니다. 실제 서버가 그 옵션을 지원하는지는 별도로 확인해야 합니다.

### HTTP 요청과 응답

`request_text()`는 딕셔너리를 JSON 바이트로 바꿔 학원 API에 POST합니다. 헤더에는 `Authorization: Bearer ...`와 `Content-Type: application/json`을 넣습니다. 자동 URL 이동을 막고, 통신 대기 시간에는 `--timeout` 값을 사용합니다.

응답 전체는 JSON이며 이 코드가 필요한 부분은 다음 경로입니다.

```text
응답 JSON
  └─ choices[0]
       ├─ message.content  → AI가 쓴 텍스트
       └─ finish_reason    → 정상 종료인지, 출력 한도로 멈췄는지
```

`request_text()`는 텍스트와 `finish_reason == 'length'` 여부를 함께 반환합니다. AI 글 자체는 Markdown 형태의 일반 텍스트입니다. 응답이 비었거나 거절됐거나 구조가 예상과 다르면 오류를 냅니다. 응답 본문은 2MB를 넘지 않게 제한합니다.

HTTP 오류가 나면 `describe_http_error()`가 상태 코드와 서버가 보내 준 설명을 읽어 안내합니다. 오류 본문을 읽다 연결이 끊겨도 가능한 범위의 설명과 원래 HTTP 상태를 보존합니다. 네트워크·인증·HTTP 오류는 자동 재요청하지 않습니다.

## 5. `formatting.py`: AI 글에서 초안 꺼내기

API가 성공해도 AI의 글을 그대로 커밋 메시지로 쓰지는 않습니다. `parse_draft(command, text)`가 먼저 제목과 본문을 구분합니다.

```text
제목: docs: 실행 안내 정리

- README에서 키 설정 방법 정리
```

PR이라면 `Why`, `What`, `How to Test` 헤더 아래의 문장도 각각 나눠 담습니다. 반환하는 `draft`는 `title`, `body`, `why`, `what`, `how_to_test` 같은 키를 가진 딕셔너리입니다. `clean_text()`는 줄바꿈을 통일하고 화면 제어 문자를 제거합니다. `one_line()`은 제목 안의 줄바꿈과 연속 공백을 한 칸으로 정리합니다.

파서는 제목 표기나 코드 블록 같은 흔한 Markdown 변형을 처리합니다. 과거 형식의 **정상적인 JSON** 응답도 `legacy_markdown()`으로 Markdown 형태로 바꿔 읽습니다. 깨진 JSON을 임의로 수선하거나 제목을 추측해서 만들어 내지는 않습니다.

제목을 찾지 못하는 등 형식을 읽을 수 없으면 `DraftFormatError`를 냅니다. PR에 제목 뒤 본문이 있지만 필수 헤더가 전혀 없는 경우도 여기에 해당합니다.

### 형식 정리 요청은 언제 하나요?

`main.py`는 `DraftFormatError`일 때만 **이미 받은 원문**을 AI에게 다시 보내 양식만 정리해 달라고 요청합니다. 기본 최대 호출 수는 2회이고 `--max-requests 1`이면 추가 요청을 하지 않습니다. 출력 한도로 잘린 응답, HTTP 오류, 네트워크 오류에는 이 경로를 사용하지 않습니다. 정리 후에도 실패하면 받은 원문을 보여 주고 사용자가 검토하도록 합니다.

## 6. `formatting.py`: 화면에 보여 줄 형태 만들기

`render_draft()`는 파싱한 값을 구분선이 있는 출력으로 조립합니다. 커밋 제목은 50자 이내를 권장하고 최대 72자, PR 제목은 최대 80자로 제한합니다. 최대 길이를 넘으면 잘라 말줄임표를 붙이고 경고합니다.

PR 본문에는 `Why`·`What`·`How to Test` 세 섹션을 항상 넣습니다. 비어 있는 섹션에는 `확인 필요` 불릿을 넣고 경고합니다. 이는 빈칸을 표시하는 **형식 처리**이지, 실제 변경 이유나 테스트 결과를 알아냈다는 뜻이 아닙니다.

마지막으로 `main.py`가 `[DONE]`과 초안을 출력합니다. 정상 종료든 오류든 `finally`에서 이번 실행의 API 호출 **시도** 횟수를 표시합니다. 출력된 글이 실제 변경을 정확히 설명하는지 확인하고 직접 고쳐 사용해야 합니다. 이 프로그램은 `git commit`, `git push`, GitHub PR 생성을 실행하지 않습니다.

## 두 명령의 흐름 비교

| 단계 | `commit` | `pr` |
| --- | --- | --- |
| Git 변경 수집·마스킹 | 동일 | 동일 |
| AI에게 요구하는 결과 | 커밋 제목과 핵심 변경 불릿 | PR 제목과 세 필수 섹션 |
| 형식 정리 | 제목·선택 본문 | 제목·Why·What·How to Test |
| 최종 사용 | 검토 후 커밋 메시지로 사용 | 검토 후 PR 제목·본문으로 사용 |

## 작은 변경 하나가 결과가 되기까지

예를 들어 `main.py`에서 오류 안내 문장을 고친 뒤 `git add main.py`를 했다고 가정해 봅시다. 다음 명령은 스테이징한 `main.py`만 분석합니다.

```bash
python3 main.py commit --staged --files main.py --safe-mode --reason "오류 안내를 이해하기 쉽게 수정"
```

1. `parse_args()`는 `command='commit'`, `staged=True`, `files=['main.py']`, `safe_mode=True` 등으로 입력을 해석합니다.
2. `collect_changes()`는 `git status`로 변경 파일을 확인하고 `git diff --cached -- main.py`로 **실제 바뀐 코드**를 읽습니다.
3. `main()`은 diff를 마스킹·제한하고 아래와 같은 정보 묶음을 만듭니다. 여기서 `diff`에는 실제 Git 비교 텍스트가 들어갑니다.

   ```text
   command    = commit
   status     = 상태 항목 1개; 분석 범위는 아래 diff만 해당
   diff       = [STAGED] ...변경된 코드...
   reason     = 오류 안내를 이해하기 쉽게 수정
   convention = 한국어, feat/fix/docs/refactor/test/chore 접두어
   truncated  = False
   ```

4. `build_payload()`는 이 문맥을 `user` 메시지에, 커밋 메시지 작성 규칙을 `system` 메시지에 넣습니다. API는 JSON으로 요청을 받지만 `message.content`에는 글을 돌려줍니다.
5. 가령 AI가 `제목: fix: 오류 안내 개선`과 변경 사항 불릿을 반환했다면, `parse_draft()`는 제목과 본문을 나눕니다. `render_draft()`는 길이와 형식을 확인해 `--- Commit Message ---` 아래에 출력할 문자열을 만듭니다.

실제 결과 문구는 매번 다를 수 있습니다. 특히 `reason`은 사람이 제공한 배경이며, diff만으로 증명되는 사실과 구분해 검토해야 합니다.

## 코드를 읽을 때 자주 만나는 Python 문법

이 프로젝트의 문법을 전체 흐름에 연결해 보면 이해하기 쉽습니다.

| 코드 모양 | 의미 | 이 프로그램에서의 쓰임 |
| --- | --- | --- |
| `def 이름(...):` | 함수를 정의 | Git 수집, 요청 구성, 초안 해석을 별도 작업으로 분리 |
| `return 값` | 호출한 곳에 결과를 돌려줌 | `collect_changes()`가 상태와 diff를 반환 |
| `status, diff = ...` | 두 결과를 변수 두 개에 나눠 담음 | Git 결과를 각자 다른 용도로 사용 |
| `{'key': value}` | 이름으로 값을 찾는 딕셔너리 | `context`, `payload`, `draft` 구성 |
| `[값1, 값2]` | 순서가 있는 리스트 | `messages`, `files`, 본문 줄 목록 |
| `if 조건:` | 조건에 따라 흐름을 나눔 | diff가 없으면 API 호출 전에 종료 |
| `for 항목 in 목록:` | 목록을 차례로 처리 | PR 섹션 조립, 요청 횟수 제한 |
| `try` / `except` | 실패를 잡아 처리 | Git·HTTP·초안 형식 오류를 안내로 바꿈 |
| `finally` | 성공·실패와 관계없이 실행 | API 호출 시도 횟수 출력 |

특히 `return 0`은 “이 함수의 일을 여기서 끝내고 정상 종료”라는 뜻입니다. 변경 사항이 없을 때 여기서 끝나므로 아래쪽 API 코드가 실행되지 않습니다. 반대로 `raise RuntimeError(...)`는 실패를 알리고 `except` 구역으로 흐름을 넘깁니다. 형식이 맞지 않을 때의 `DraftFormatError`는 별도로 잡아 **양식 정리 요청**을 할 수 있게 만든 예외입니다.

### 직접 따라 읽기

1. `main.py`의 `parse_args()`와 `main()`을 보며 위 예시 명령이 `args`에 어떻게 저장되는지 확인합니다.
2. `git_context.py`의 `collect_changes()`에서 `--staged`가 있을 때와 없을 때 실행하는 Git 명령을 비교합니다.
3. `main.py`에서 `context`가 만들어지는 지점을 찾고 `--dry-run`으로 요청 본문을 확인합니다.
4. `ai_client.py`의 `build_payload()`에서 `commit`과 `pr`의 지침을 비교합니다.
5. `formatting.py`의 `parse_draft()`와 `render_draft()`를 보며 텍스트가 제목·본문으로 나뉘고 다시 출력되는 과정을 확인합니다.

이 순서로 보면 한 함수의 모든 문법을 처음부터 이해하지 못해도 **입력 → 가공 → 출력**의 연결을 먼저 잡을 수 있습니다.
