# 실행 기록

기록 시각: 2026-10-08T15:59:29+09:00

실제 Gemini REST 호출 결과입니다.

입력 diff SHA-256: `0dd8b5a385445262f62735fe325c81fc6f17a2febb761709cf6f29c9054ed8f6`. 모든 생성 실행에 같은 diff/reason/test를 사용했습니다.

| 실행 로그 | 종료 코드 | stdout 문자 수 | 제목 |
| --- | --- | --- | --- |
| [no-changes](no-changes.txt) | 0 | 90 |  |
| [missing-key](missing-key.txt) | 1 | 95 |  |
| [request-preview](request-preview.txt) | 0 | 1864 |  |
| [commit](commit.txt) | 0 | 381 | chore: app.py 출력값 1에서 2로 변경 |
| [pr-baseline](pr-baseline.txt) | 0 | 445 | app.py 출력값 변경 |
| [pr-temperature](pr-temperature.txt) | 0 | 454 | app.py 샘플 출력 기대값 변경 |
| [pr-small-budget](pr-small-budget.txt) | 1 | 174 |  |
| [pr-large-budget](pr-large-budget.txt) | 0 | 445 | app.py 출력값 변경 |

stdout 문자 수는 로그를 포함하므로 토큰 수나 품질 점수가 아닙니다.

pr-baseline ↔ pr-temperature는 temperature만, pr-baseline ↔ pr-small-budget/pr-large-budget는 max_tokens만 바꿨습니다. 각 조건 1회라 인과관계·재현성을 입증하지는 않습니다.

작은 예산이 실패하면 오류 로그에서 MAX_TOKENS를 확인하세요. 예산을 늘려도 답변이 반드시 길어지지는 않습니다. 두 성공 초안의 표현·내용 차이는 원문 로그를 직접 비교하세요.
