"""AI의 Markdown 초안을 읽고 제목 길이와 PR 섹션을 정리한다."""
import json
import re


class DraftFormatError(ValueError):
    """형식 정리 요청을 한 번 더 시도할 수 있는 오류."""


def clean_text(value):
    if not isinstance(value, str):
        return ''
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    value = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', value)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', value).strip()


def one_line(value):
    return ' '.join(clean_text(value).split())


def heading_kind(line):
    name = line.strip().strip('#*- ').strip().rstrip(':：').strip().casefold()
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()
    names = {
        'why': 'why', '변경 배경': 'why',
        'what': 'what', '변경 사항': 'what',
        'how to test': 'how_to_test', '테스트 방법': 'how_to_test',
        'title': 'title', '제목': 'title', 'pr title': 'title',
        'commit message': 'title', 'pr body': 'body', 'body': 'body', '본문': 'body',
    }
    return names.get(name)


def legacy_markdown(text, command):
    """JSON 문법을 임의로 수선하지 않고 정상 객체만 Markdown으로 바꾼다."""
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError('객체가 아님')
        data = data.get(command, data)
        if not isinstance(data, dict):
            raise ValueError('내부 객체가 아님')
        title = data.get('title') or data.get(command + '_title')
        if not one_line(title):
            raise ValueError('제목 없음')
        lines = ['제목: ' + one_line(title)]
        fields = [('body', 'Body')]
        if command == 'pr':
            fields = [('why', 'Why'), ('what', 'What'), ('how_to_test', 'How to Test')]
        body = data.get('body', data.get('pr_body', {}))
        for key, header in fields:
            value = data.get(key, data.get(header))
            if value is None and isinstance(body, dict):
                value = body.get(key, body.get(header))
            if isinstance(value, list):
                value = '\n'.join('- ' + item for item in value if isinstance(item, str))
            if isinstance(value, str) and value.strip():
                lines.extend(['## ' + header, value])
        if command == 'pr' and isinstance(body, str):
            lines.append(body)
        return '\n'.join(lines)
    except (ValueError, TypeError) as exc:
        raise DraftFormatError('AI가 요청한 Markdown 대신 불완전한 JSON을 반환했습니다.') from exc


def parse_draft(command, content):
    text = clean_text(content)
    if not text:
        raise DraftFormatError('AI 응답이 비어 있습니다.')
    fenced = re.fullmatch(r'```(?:markdown|md|text|json)?\s*\n(.*?)\n```', text, re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    # 과거 JSON 형식도 정상 구조일 때만 호환 변환한다.
    if text.startswith(('{', '[')):
        text = legacy_markdown(text, command)
    draft = {'title': '', 'body': [], 'why': [], 'what': [], 'how_to_test': []}
    current = None
    waiting_title = False
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
        label = re.match(r'^(?:#{1,6}\s*)?\**(?:제목|title|pr title|commit title)\**\s*[:：]\s*\**\s*(.+)$', stripped, re.I)
        if label and not in_code and not draft['title']:
            draft['title'] = one_line(label.group(1)).strip('*` ')
            waiting_title = False
            current = 'body'
            continue
        kind = None if in_code else heading_kind(stripped)
        if kind == 'title':
            waiting_title = not bool(draft['title'])
            continue
        if kind in ('why', 'what', 'how_to_test', 'body'):
            current = kind
            waiting_title = False
            continue
        candidate = stripped.strip('#*` ')
        conventional = re.match(r'^(feat|fix|docs|refactor|test|chore|perf|style|build|ci|revert)(\([^\n]*\))?!?:\s*\S', candidate, re.I)
        if not draft['title'] and candidate and (waiting_title or conventional):
            draft['title'] = one_line(candidate)
            waiting_title = False
            current = 'body'
            continue
        if draft['title'] and current:
            draft[current].append(line)
    # 제목을 추측해서 성공으로 처리하지 않고 형식 정리를 요청한다.
    if not draft['title']:
        raise DraftFormatError('응답에서 제목을 확인하지 못했습니다.')
    if command == 'pr' and draft['body'] and not any(draft[key] for key in ('why', 'what', 'how_to_test')):
        raise DraftFormatError('PR 본문에 Why/What/How to Test 구분이 없습니다.')
    return draft


def section_text(lines, label):
    text = '\n'.join(lines).strip()
    # 비어 있는 섹션은 사실을 채우는 대신 사람이 보완할 자리로 표시한다.
    if not text:
        return '- ' + label + ' 확인 필요: 작성자가 내용을 보완하세요.'
    if not re.search(r'^\s*[-*+]\s+\S', text, re.M):
        text = '- ' + text
    return text


def render_draft(command, draft):
    warnings = []
    title = one_line(draft['title'])
    limit = 72 if command == 'commit' else 80
    if len(title) > limit:
        title = title[:limit - 1].rstrip() + '…'
        warnings.append('제목을 길이 제한에 맞춰 줄였습니다. 의미를 검토하세요.')
    elif command == 'commit' and len(title) > 50:
        warnings.append('커밋 제목은 50자 이내를 권장합니다.')
    if command == 'commit':
        body = '\n'.join(draft['body']).strip()
        if body:
            body = '\n\n' + section_text(draft['body'], '핵심 변경')
        return f'--- Commit Message ---\n{title}{body}\n----------------------', warnings
    sections = []
    for field, header in [('why', 'Why'), ('what', 'What'), ('how_to_test', 'How to Test')]:
        if not any(line.strip() for line in draft[field]):
            warnings.append(header + ' 내용이 없어 확인 필요로 표시했습니다.')
        sections.append('## ' + header + '\n' + section_text(draft[field], header))
    if any(line.strip() for line in draft['body']):
        sections.append('## 추가 메모\n' + '\n'.join(draft['body']).strip())
    body = '\n\n'.join(sections)
    return f'--- PR Title ---\n{title}\n\n--- PR Body ---\n{body}\n----------------------', warnings
