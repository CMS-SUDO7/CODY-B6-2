# 모듈별 유지보수와 유닛 테스트

테스트 실행: 저장소 루트에서 `python -m unittest discover -s tests -v`. 표준 라이브러리만 사용하고 외부 API 호출은 하지 않습니다. 실행 가능한 샘플은 [tests/test_modules.py](../tests/test_modules.py)에 있습니다.

| 수정 대상 | 유지해야 할 계약 | 검사 방법 |
| --- | --- | --- |
| git_changes.py | 루트에서 수집, 원본 저장소 변경 없음, staged/unstaged 구분, untracked는 경로만 | GitTests: 임시 Git 저장소에서 수집·공백 rename·하위 경로 거부 검사 |
| gemini_api.py | contents/generationConfig 구조, 키는 헤더만, generateContent 1회, STOP만 성공 | ApiTests: urlopen을 모의 응답으로 대체해 실제 POST JSON과 호출 수, HTTP·네트워크·절단·JSON 실패 검사 |
| cli.py | 기존 명령·옵션·기본값 유지, 잘못된 입력은 종료 코드 2 | FormatAndCliTests 및 main.py --help: 옵션 해석과 CLI 동작 확인 |
| main.py | 사용자 오류 안내, 호출 수, 옵션 전달, dry-run 네트워크 0회 | FormatAndCliTests 및 capture_evidence.py: CLI 실행과 stdout/stderr 확인 |
| output_format.py | title 최대 길이, 커밋 불릿 2개, PR 필수 섹션, 사실 미확인 표시 | FormatAndCliTests: 누락 필드·권장 예시·길이 경계 검사 |
| safety.py | 길이 제한 전에 마스킹, 생략 표시 유지 | tests/test_safety.py: 이름·인용·다중행·인증 헤더·URL·이메일, 실제 요청 본문과 출력 검사 |

Git 수집 수정 시 실제 사용자의 저장소 대신 TemporaryDirectory에서 자료를 만듭니다. status의 NUL 구분을 유지해야 공백·줄바꿈 경로를 정확히 구분할 수 있습니다. 프롬프트 필드를 바꾸면 format_draft와 대응 테스트도 함께 수정합니다. REST 필드명을 바꾸면 build_payload와 테스트에서 CLI→POST 매핑을 확인합니다. 단순히 함수가 실행되는지만 검사하지 말고 잘못된 옵션 전달, 중복 요청, 미완료 초안 성공 처리 같은 사용자에게 영향을 주는 오류를 잡습니다.

새 API 오류를 지원할 때는 ApiTests의 패턴으로 응답을 구성하고 예상 메시지·종료 코드·비밀값 제외 여부를 검증합니다. 테스트의 모의 응답은 모델의 생성 품질을 검증하지 않으므로 프롬프트 변경 후에는 별도로 실제 Gemini 결과를 읽고 diff 근거와 테스트 주장도 검토합니다. 네트워크 테스트를 기본 유닛 테스트에 섞지 않습니다.

실제 생성 검증: `python scripts/capture_evidence.py --live`. 샘플 저장소에서만 변경·커밋하며 사용자의 작업 트리와 index를 조작하지 않습니다. 실험 조건을 추가하면 diff를 고정하고 한 번에 한 옵션만 바꾸세요. 원시 로그와 manifest를 함께 제출하고 실패도 보존합니다. 실제 키·환경파일은 커밋하지 않습니다.

마스킹 수정 시 [민감정보 처리 점검](sensitive_data.md)의 범위를 확인합니다. 보호가 필요한 값은 가짜 자료로 만들고 테스트에만 넣으세요. 새 비밀값 표기를 지원하면 일반 코드·JSON 이웃 필드·숫자 출력 예산이 과도하게 가려지지 않는지도 확인합니다. 외부 API로 실제 개인정보를 보내 마스킹을 시험하지 않습니다.
