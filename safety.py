"""전송할 문자열을 마스킹하고 diff 크기를 제한한다."""

import re


# 이름이 있는 비밀값을 탐지한다. 숫자·하이픈·camelCase·한글 이름도 포함한다.
_SECRET_NAME = (
    r"[\w.-]*(?:api[ _-]?key|pass(?:word|wd|phrase)|pwd|secret|token|"
    r"private[ _-]?key|access[ _-]?key|비밀번호|패스워드|암호|비밀[ ]?키|인증[ ]?키|토큰)[\w.-]*"
)
_ASSIGNMENT = re.compile(
    r"(?<![\w.-])(?P<quote>(?:\\?[\"'])?)(?P<name>" + _SECRET_NAME
    + r")(?P=quote)[ \t]*(?:=>|[:=])[ \t]*", re.IGNORECASE,
)


def _quoted_end(text: str, start: int, quote: str) -> int:
    """일반 리터럴과 JSON 문자열 안의 이스케이프된 인용 값을 읽는다."""
    end = start + len(quote)
    while end < len(text):
        if quote.startswith("\\") and text[end] == "\\":
            last = end
            while last < len(text) and text[last] == "\\":
                last += 1
            if last < len(text) and text[last] == quote[-1]:
                if (last - end) % 4 == 1:
                    return last + 1
                end = last + 1
                continue
        if text.startswith(quote, end):
            return end + len(quote)
        if text[end] == "\\":
            end += 2
        else:
            end += 1
    return len(text)


def _compound_end(text: str, start: int) -> int:
    """여러 줄 괄호 표현식 전체를 가려 다음 줄 값이 남지 않게 한다."""
    stack = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    end = start
    while end < len(text):
        quote = next((item for item in ('"""', "'''", '"', "'")
                      if text.startswith(item, end)), "")
        if quote:
            end = _quoted_end(text, end, quote)
            continue
        char = text[end]
        if char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
            if not stack:
                return end + 1
        end += 1
    return len(text)


def _mask_assignments(text: str) -> str:
    """따옴표 값·여러 줄 리터럴·YAML 블록을 값 끝까지 가린다."""
    pieces = []
    cursor = 0
    for match in _ASSIGNMENT.finditer(text):
        if match.start() < cursor:
            continue
        start = match.end()
        line_end = text.find("\n", start)
        if line_end == -1:
            line_end = len(text)
        value = text[start:line_end].rstrip("\r")
        name = match.group("name").casefold()
        if name in ("max_tokens", "maxoutputtokens") and re.fullmatch(r"\d+\s*[,)}\]]?\s*", value):
            continue
        # JSON 값이 다음 줄에 오는 경우도 따옴표 시작 위치를 찾는다.
        quote_start = start
        if not value.strip():
            following = re.match(r"\s*(?:[+-][ \t]*)?", text[start:])
            quote_start += following.end()
        quote = next((item for item in ('"""', "'''", '"', "'", '\\"', "\\'")
                      if text.startswith(item, quote_start)), "")
        replacement = "[REDACTED]"
        if quote:
            end = _quoted_end(text, quote_start, quote)
            replacement = quote + "[REDACTED]" + quote
        elif quote_start < len(text) and text[quote_start] in "([{":
            end = _compound_end(text, quote_start)
        elif not value.strip() or re.fullmatch(r"[|>][+-]?[1-9]?(?:[ \t]+#.*)?", value):
            # diff의 +/- 접두사를 제외한 들여쓰기로 YAML 블록 끝을 찾는다.
            line_start = text.rfind("\n", 0, match.start()) + 1
            prefix = text[line_start:match.start()].lstrip("+-")
            indent = len(prefix) - len(prefix.lstrip(" \t"))
            end = line_end
            offset = line_end + 1
            for line in text[offset:].splitlines(keepends=True):
                logical = line.lstrip("+-")
                next_indent = len(logical) - len(logical.lstrip(" \t"))
                if logical.strip() and next_indent <= indent:
                    break
                end = offset + len(line.rstrip("\r\n"))
                offset += len(line)
            if end == line_end and not value.strip():
                continue
        else:
            # 따옴표 없는 값은 같은 줄의 나머지를 보수적으로 가린다.
            end = line_end
        pieces.extend((text[cursor:start], replacement))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def mask_sensitive(text: str, api_key: str = "") -> str:
    """알려진 키, 이메일, 비밀값 할당 패턴을 가린다. 완전한 탐지는 아니다."""
    if api_key:
        text = text.replace(api_key, "[REDACTED_KEY]")
    # 연결 URL의 사용자명·비밀번호는 특수문자·퍼센트 인코딩까지 함께 가린다.
    text = re.sub(r"(?i)([a-z][a-z0-9+.-]*://)[^\s/<>\"']+@", r"\1[REDACTED]@", text)
    # Bearer/Basic은 값의 형태와 관계없이 헤더의 줄 끝까지 가린다.
    text = re.sub(
        r"(?im)((?:[\"']?(?:proxy[-_])?authorization[\"']?[ \t]*[:=][ \t]*|"
        r"\b(?:Bearer|Basic)[ \t]+))[^\r\n]+", r"\1[REDACTED]", text,
    )
    text = re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|\Z)",
        "[REDACTED_PRIVATE_KEY]", text,
    )
    text = _mask_assignments(text)
    patterns = [
        r"AIza[A-Za-z0-9_-]{35}",
        r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{16,}",
        r"AKIA[A-Z0-9]{16}",
        r'(?:"[^"\r\n]+"|[\w.!#$%&\x27*+/=?^`{|}~-]+)@(?:[\w-]+\.)+[\w-]{2,}',
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


def prepare_input(status: str, diff: str, reason: str, test: str,
                  safe_mode: bool, api_key: str) -> tuple[dict, bool]:
    """AI에 보낼 자료와 일부 생략 여부를 반환한다."""
    omitted = False
    if safe_mode:
        # 잘라 내기 전에 마스킹해야 경계에서 잘린 비밀값도 노출되지 않는다.
        status = mask_sensitive(status, api_key)
        diff = mask_sensitive(diff, api_key)
        reason = mask_sensitive(reason, api_key)
        test = mask_sensitive(test, api_key)
    if safe_mode:
        lines = []
        file_count = 0
        for line in diff.splitlines():
            if line.startswith("diff --git "):
                file_count += 1
            if file_count > 10 or len(lines) >= 200:
                omitted = True
                break
            # 한 줄짜리 매우 큰 변경도 최대 1,000자로 제한한다.
            if len(line) > 1000:
                omitted = True
            lines.append(line[:1000])
        diff = "\n".join(lines)
    data = {"status": status, "diff": diff, "reason": reason, "test": test}
    if safe_mode:
        for name, value in data.items():
            if len(value) > 20000:
                omitted = True
            data[name] = value[:20000]
    data["omitted"] = omitted
    return data, omitted
