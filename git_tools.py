"""저장소를 바꾸지 않고 Git 변경 정보를 수집한다."""

from pathlib import Path
import subprocess


def run_git(arguments: list[str]) -> str:
    """Git 명령의 표준 출력을 반환하고 실패를 ValueError로 알린다."""
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", *arguments],
            capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except FileNotFoundError as error:
        raise ValueError("Git을 설치하고 터미널을 다시 열어 주세요.") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError("Git 명령이 30초 안에 끝나지 않았습니다.") from error
    if result.returncode != 0:
        raise ValueError("Git 명령 실패: " + result.stderr.strip())
    return result.stdout


def collect_changes() -> tuple[str, str, int, int]:
    """상태, diff, 변경 항목 수, 미추적 항목 수를 반환한다."""
    root = run_git(["rev-parse", "--show-toplevel"]).strip()
    if Path.cwd().resolve() != Path(root).resolve():
        raise ValueError("Git 프로젝트 루트 디렉터리에서 실행해 주세요: " + root)
    # -z는 파일명에 공백이나 줄바꿈이 있어도 항목을 구분할 수 있게 한다.
    records = run_git(["status", "--porcelain=v1", "-z"]).split("\0")
    statuses = []
    untracked = 0
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        code = record[:2]
        if "U" in code or code in ("AA", "DD"):
            raise ValueError("병합 충돌을 해결한 뒤 다시 실행해 주세요.")
        statuses.append(record)
        if code == "??":
            untracked += 1
        # 이름 변경/복사에서는 다음 항목이 원래 경로이므로 따로 소비한다.
        if "R" in code or "C" in code:
            statuses[-1] += " <- " + records[index]
            index += 1
    if not statuses:
        return "", "", 0, 0
    # 인덱스 변경과 작업 폴더 변경을 구분해 같은 파일의 두 상태도 보여 준다.
    options = ["--no-ext-diff", "--no-textconv", "--no-color"]
    staged = run_git(["diff", "--cached", *options])
    unstaged = run_git(["diff", *options])
    diff = "[STAGED]\n" + staged + "\n[UNSTAGED]\n" + unstaged
    return "\n".join(statuses), diff, len(statuses), untracked
