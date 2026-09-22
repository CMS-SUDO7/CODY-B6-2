"""Git 조회와 전송 전 민감정보 처리를 담당한다."""
import os
import re
import subprocess
from pathlib import Path


def run_git(*arguments):
    """셸을 거치지 않고 Git 조회 명령을 실행한다."""
    try:
        result = subprocess.run(
            ['git', *arguments], capture_output=True, text=True,
            encoding='utf-8', errors='replace', check=True, timeout=15,
        )
    except FileNotFoundError as exc:
        raise RuntimeError('Git이 없습니다. Git 설치 후 다시 실행하세요.') from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Git 조회 시간이 15초를 초과했습니다.') from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError('Git 조회 실패: 저장소 접근 권한과 Git 상태를 확인하세요.') from exc
    return result.stdout


def collect_changes(staged_only=False, paths=None):
    """프로젝트 루트에서 status와 diff만으로 변경을 수집한다."""
    if not Path('.git').exists():
        raise RuntimeError('Git 프로젝트 루트에서 실행하세요. 새 폴더는 먼저 git init을 실행하세요.')
    status = run_git('status', '--short', '--branch', '--untracked-files=all')
    # Git에 등록된 외부 도구를 실행하지 않고 텍스트 차이만 읽는다.
    options = ['diff', '--no-ext-diff', '--no-textconv', '--no-color', '--unified=3']
    paths = paths or []
    staged = run_git(*options, '--cached', '--', *paths)
    unstaged = ''
    if not staged_only:
        unstaged = run_git(*options, '--', *paths)
    diff = ''
    if staged:
        diff += '[STAGED]\n' + staged
    if unstaged:
        diff += '[UNSTAGED]\n' + unstaged
    return status, diff


def mask_text(text):
    """대표 패턴을 가리지만 모든 개인정보 탐지를 보장하지는 않는다."""
    text = redact_key(text)
    # 전송량을 자르기 전에 마스킹해야 여러 줄 개인키를 통째로 찾을 수 있다.
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', '[PRIVATE KEY MASKED]', text, flags=re.S)
    text = re.sub(r'(?i)\b(?:api[_-]?key|token|secret|password)\b[\x22\x27]?\s*[:=][^\r\n]*', '[SECRET MASKED]', text)
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]+)\b', '[KEY MASKED]', text)
    text = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[EMAIL MASKED]', text)
    return text


def redact_key(text):
    key = os.environ.get('AI_API_KEY', '').strip()
    if key:
        text = text.replace(key, '[API KEY MASKED]')
    return text


def limit_diff(diff, max_files, max_lines):
    """한 파일이 두 영역에 있으면 두 블록으로 계산한다."""
    selected = []
    files = 0
    lines = diff.splitlines()
    for line in lines:
        if line.startswith('diff --git '):
            files += 1
        if files > max_files or len(selected) >= max_lines:
            break
        selected.append(line)
    return '\n'.join(selected), len(selected) < len(lines)
