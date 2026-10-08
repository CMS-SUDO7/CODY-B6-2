# GitHub 등록과 기능별 작업 흐름

저장소: [CMS-SUDO7/CODY-B6-2](https://github.com/CMS-SUDO7/CODY-B6-2) · 공개 · 기본 브랜치 `main`

이미 구현되어 있던 소스를 기능별로 나누어 처음 등록했습니다. 최초 개발 당시의 시간을 재현한 이력이 아니라, 공개 저장소에 등록한 실제 커밋·push·병합 이력입니다.

## 등록 순서

먼저 `.gitignore`와 `requirements.txt`만 초기 커밋으로 `main`에 push했습니다. 이후 각 단계를 현재 `main`에서 분기하고 해당 기능의 파일만 커밋했습니다. 기능 브랜치를 먼저 push하고, `main`에서 `--no-ff`로 병합한 다음 `main`을 다시 push했습니다. 원격 기능 브랜치는 작업 흐름을 확인할 수 있도록 보관합니다.

| 순서 | 브랜치 | 등록 파일 | 역할 |
| --- | --- | --- | --- |
| 1 | `main` 초기 설정 | `.gitignore`, `requirements.txt` | Python 프로젝트 설정과 로컬 파일 제외 |
| 2 | `feat/git-change-collection` | `git_tools.py` | 저장소 루트 확인, status와 staged/unstaged diff 수집 |
| 3 | `feat/safe-input` | `safety.py` | 민감값 마스킹, 입력 길이·파일 블록 제한 |
| 4 | `feat/draft-formatting` | `output_format.py` | 커밋 제목·불릿, PR 제목·필수 섹션 후처리 |
| 5 | `feat/gemini-api` | `gemini_api.py` | 프롬프트 작성, Gemini REST 요청·응답·오류 처리 |
| 6 | `feat/cli` | `main.py` | 옵션 검증과 수집→생성→출력 흐름, dry-run |
| 7 | `docs/project-guides` | `README.md`, 학습 문서, 과제 PDF, 이 문서 | 실행 방법, 소스 해설, GitHub 작업 흐름 안내 |

기능 브랜치별 작업은 다음 순서입니다. `git add`에는 해당 기능의 파일만 지정합니다.

```powershell
git switch -c feat/git-change-collection main
git add git_tools.py
git commit -m "feat: collect staged and unstaged Git changes"
git push -u origin feat/git-change-collection
git switch main
git merge --no-ff feat/git-change-collection -m "merge: integrate Git change collection"
git push origin main
```

초기 설정을 포함한 7개의 등록 커밋과 기능·문서 브랜치의 6개 병합 커밋이 남습니다. 브랜치 병합은 Git으로 수행했으며, GitHub Pull Request는 별도로 만들지 않았습니다.

## GitHub에서 확인하기

- [최종 소스와 파일 구조](https://github.com/CMS-SUDO7/CODY-B6-2/tree/main)
- [전체 커밋 이력](https://github.com/CMS-SUDO7/CODY-B6-2/commits/main/)
- [보관한 작업 브랜치](https://github.com/CMS-SUDO7/CODY-B6-2/branches)
- [브랜치 병합 그래프](https://github.com/CMS-SUDO7/CODY-B6-2/network)

로컬에서도 다음 명령으로 같은 흐름을 확인할 수 있습니다.

```powershell
git log --graph --oneline --decorate --all
git branch -a
git ls-tree -r --name-only origin/main
```

## 업로드에서 제외한 파일

`verification.md`는 `.gitignore`에 등록하여 로컬에만 보관합니다. 어느 브랜치나 커밋에도 포함하지 않습니다. 환경 파일, 키 파일, Python 캐시도 기존 제외 규칙을 유지합니다.

## 등록 전 로컬 확인

2026-10-08 Windows PowerShell, Python 3.14.4, Git 2.54.0 환경에서 다음을 확인했습니다.

- Python 소스 문법과 CLI 도움말
- 이메일 마스킹과 안전 모드의 diff 길이 제한
- 커밋 제목 길이 보정, PR의 Why/What/How to Test 섹션
- 임시 Git 저장소에 staged 파일을 만든 뒤 commit/pr dry-run 실행
- dry-run의 실제 Gemini API 호출 횟수 0회

실제 Gemini API 호출은 수행하지 않았습니다.
