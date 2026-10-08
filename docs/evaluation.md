# 사전평가 보완과 제출 증거

2026-10-08 평가 피드백에 맞춰 보완했습니다. 코드·문서를 작성했다는 사실과 실제 모델이 생성했다는 사실을 구분합니다. 아래 스크립트는 출력 문자열을 손으로 만든 제출 예시 대신 실제 CLI stdout/stderr를 파일로 저장합니다.

## 실행 로그 생성

```powershell
# API 없이 실제 CLI/Git/후처리 실행, HTTP 계층만 모의 응답
python scripts/capture_evidence.py
# 실제 Gemini 생성 요청 5회 (자동 재시도 없음)
python scripts/capture_evidence.py --live
# 검증 전용 키 파일을 직접 지정하는 대안 (main.py의 .env 자동 로딩은 아님)
python scripts/capture_evidence.py --live --key-file .env
```

`--live`는 유효한 GEMINI_API_KEY와 연결이 필요합니다. `.env`는 로컬의 `GEMINI_API_KEY=키` 한 줄만 읽고 키를 출력하지 않습니다. 생성기의 평소 실행은 기존대로 환경변수만 사용합니다. 모델이 계정에서 제공되지 않으면 스크립트에 `--model 사용가능한_Gemini_모델명`을 지정합니다.

샘플 Git 저장소에 app.py의 `print(1) → print(2)` 변경을 스테이징합니다. `python app.py`의 실제 출력 2와 종료 코드 0을 먼저 확인한 다음 같은 diff/reason/test로 모든 생성 명령을 실행합니다. 원본 저장소에서 변경을 만들거나 실제 커밋을 생성하지 않습니다. 생성 요청 5회는 커밋 1회, PR 조건 4회입니다. 키 없음·변경 없음·dry-run은 생성 요청 0회입니다.

로그는 [docs/evidence/mock](evidence/mock/README.md) 또는 [docs/evidence/live](evidence/live/README.md)에 저장됩니다. 각 폴더에 명령·실행 시각·종료 코드·stdout·stderr, 동일 입력 diff, 요청 본문, 조건 manifest, 요약표가 있습니다. mock은 외부 AI 호출이 없어 실제 모델의 표현 차이를 입증하지 못합니다. live에서 성공한 commit/pr 생성 로그가 실제 API 결과 증거입니다. 로그는 실제 호출을 재시도하지 않으며 64토큰 예산의 절단 오류도 그대로 기록합니다. 재실행하면 해당 모드의 기존 로그를 덮어씁니다.

## 항목별 보완 위치

| 평가 | 보완 | 검토 자료 |
| --- | --- | --- |
| #1, #2 FAIL | 실제 Gemini commit/pr 출력 로그 추가 | [커밋 출력](evidence/live/commit.txt), [PR 출력](evidence/live/pr-baseline.txt) |
| #6 FAIL | 동일 입력에서 temperature만 또는 max_tokens만 바꾸는 실제 실험 | [조건·결과 요약](evidence/live/README.md), [manifest](evidence/live/manifest.json), [실제 비교 결과](design.md) |
| #10 FAIL | 모델 교체·실험·재현 목적과 CLI 사용 사례 | [설계와 옵션 비교: 옵션 선택과 비교](design.md) |
| #12 FAIL | 샘플링 확률·표현 다양성·제목/섹션 일관성 설명 | [설계와 옵션 비교: temperature](design.md) |
| #13 FAIL | 입력/출력 한도, 공유 컨텍스트 예산의 가상 예시, 절단 실패 처리 | [설계와 옵션 비교: max_tokens](design.md), [절단 로그](evidence/live/pr-small-budget.txt) |
| #15 FAIL | 후처리/재생성의 정확도·제어·지연·비용 비교 | [설계와 옵션 비교: 프롬프트와 후처리](design.md) |
| #3, #4 PASS 보완 | 키 설정 한 줄 안내, 변경 없음의 브랜치·작업 트리 상태 | main.py 및 missing-key/no-changes.txt |
| #5, #7 PASS 보완 | PR 작성 템플릿, 위반 필드별 권장 수정 예시 | [PR 초안 검토](design.md) 및 output_format.py |
| #8, #9 PASS 보완 | Git/AI 실행 가능한 유닛 테스트와 분리 설계 이유 | tests/test_modules.py, [유지보수 지침](maintenance.md), [프롬프트와 후처리](design.md) |
| #11 PASS 보완 | 자주 발생하는 오류별 조치와 명령 | [README: 오류 해결](../README.md) |
| #14 PASS 보완 | dry-run에서 실제 요청과 같은 JSON 구조 확인 | gemini_api.py: build_payload, [미전송 요청 미리보기](evidence/live/request.json) |
| #16 PASS 보완 | 사실·테스트·편향·민감정보 검토 체크리스트 | [설계와 옵션 비교: PR 초안 검토](design.md) |

temperature는 각 조건 1회만 측정하므로 관측한 표현 차이가 설정 때문이라는 통계적 결론을 내리지 않습니다. 입력·모델·시간을 기록하고 실제 diff에 맞는지 읽어 보세요. max_tokens는 목표 길이가 아니므로 예산을 늘려도 길이가 비슷할 수 있습니다. 작은 예산의 실패와 큰 예산의 완료 여부를 함께 보고 한도 의미를 설명합니다.

## 현재 확인 상태

Windows / Python 3.14.4 / Git 2.54.0에서 [모듈 테스트 15개 통과](evidence/test-results.txt). 2026-10-08 15:59 KST에 사용자가 키를 설정한 터미널에서 `--live` 실행을 시작했고, 완료된 실제 Gemini 로그와 조건 manifest를 저장했습니다. 생성 요청은 총 5회였으며 commit·기준 PR·temperature 변경 PR·큰 예산 PR은 종료 코드 0입니다. 작은 예산 PR은 예상한 `MAX_TOKENS`로 종료 코드 1이며 완성 초안을 출력하지 않았습니다.

#1/#2의 실제 생성 출력과 #6의 옵션 비교 증거를 추가했습니다. temperature 0.2/1.2에서 제목 표현 차이를 관측했고, max_tokens 64에서는 절단, 2048/4096에서는 완성을 확인했습니다. 2048/4096의 PR 본문은 같았습니다. 상세 비교는 [실제 비교 결과](design.md)와 원문 로그를 참고하세요. 이는 제출 자료 보완 결과이며 학원의 재평가 판정을 대신하지 않습니다.

추가 민감정보 점검: 비밀번호 별칭·한글 표기·여러 줄 값·인증 헤더·연결 URL 등 누락 형태를 보완했습니다. 현재 [전체 테스트는 34개 통과](evidence/sensitive-test-results.txt)이며, [형식별 범위와 한계](sensitive_data.md)를 함께 기록했습니다. 이 검증은 가짜 자료와 모의 REST로 수행했으며 기존 실제 Gemini 실행 로그를 다시 생성하지 않았습니다.

## 요구사항 확인

| 요구사항 | 구현 파일·함수 | 확인 방법 | 확인 결과 |
| --- | --- | --- | --- |
| Python 3.10 이상 터미널 CLI | `cli.py: parse_args`, `main.py: main` | help·컴파일·임시 저장소 실행 | Python 3.12.14 및 Windows/Python 3.14.4 기본 동작 통과, 3.10 직접 실행은 미확인 |
| Git 루트 실행 | `git_changes.py: collect_changes` | 비Git/하위 디렉터리에서 실행 | 거부 확인 |
| status 변경 목록/diff 수집 | `collect_changes/run_git` | 실제 임시 Git 저장소 | 신규·수정·staged+unstaged·rename·빈 파일·binary 확인 |
| 변경 없을 때 종료 | `main` | 빈 저장소에서 키 없이 실행 | 메시지 출력, 요청 0회 |
| 환경변수 키 사용 | `main` | 키 미설정/모의 환경변수 | 누락 안내, 코드에 실제 키 없음 |
| AI API 요청과 출력 | `gemini_api.py: generate`, `main` | 실제 Gemini 및 모의 REST로 CLI 끝까지 실행 | [실제 commit/pr 성공](evidence/live/README.md), 각 요청 1회 |
| 모델/temperature/max_tokens 옵션 | `cli.py: parse_args`, `gemini_api.py: generate` | 범위 오류·POST JSON 검사 | 기본값/전달/경계 확인 |
| API 실패 원인 안내 | `generate/main` | HTTP 400/401/403/404/429/500·연결 오류 모의 | 원인 안내, 키 마스킹 확인 |
| 커밋 제목 1줄·본문 불릿 | `build_prompt/format_draft` | 모의 생성/길이 초과 출력 | 최대 72자·권장 경고·불릿 2개 확인 |
| PR 제목·Why/What/How to Test | `format_draft/get_items` | 누락·잘못된 타입을 가진 출력 | 최대 80자·3개 헤더·각 불릿 보충 확인 |
| 구획을 나눈 최종 출력 | `main` | 모의 CLI 출력 | 변경 요약/초안 구분 확인 |
| 실행당 요청 1~2회 이하 | `generate/main` | 요청 호출 수 계측 | 정상/실패 1회; 재시도 없음 |
| 안전 모드 제공 | `safety.py: mask_sensitive/prepare_input` | 키/이메일/PEM/200줄/10블록/장문 | 마스킹과 제한 확인 |
| README 필수 안내 | [README](../README.md) | 문서 검토 | 설치·키·명령·예시·한도·보안 안내 작성 |
| GitHub 소스 push | 기능별 브랜치와 `main` 병합 | 원격 파일·커밋·브랜치 확인 | [공개 저장소](https://github.com/CMS-SUDO7/CODY-B6-2) |

기능별 브랜치와 병합 기록은 [커밋 이력](https://github.com/CMS-SUDO7/CODY-B6-2/commits/main/)과 [브랜치 목록](https://github.com/CMS-SUDO7/CODY-B6-2/branches)에서 확인할 수 있습니다.
