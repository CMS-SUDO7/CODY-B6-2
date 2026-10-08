"""전송할 문자열을 마스킹하고 diff 크기를 제한한다."""

import re


def mask_sensitive(text: str, api_key: str = "") -> str:
    """알려진 키, 이메일, 비밀값 할당 패턴을 가린다. 완전한 탐지는 아니다."""
    if api_key:
        text = text.replace(api_key, "[REDACTED_KEY]")
    patterns = [
        r"AIza[A-Za-z0-9_-]{35}",
        r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{16,}",
        r"AKIA[A-Z0-9]{16}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)
    # 키 이름은 남기고 같은 줄의 할당 값은 가린다.
    def mask_assignment(match: re.Match) -> str:
        # 출력 예산의 숫자는 인증 토큰이 아니다. 알려진 두 옵션만 숫자일 때 보존한다.
        prefix, value = match.groups()
        numeric_budget = re.search(r"(?i)\b(?:max_tokens|maxOutputTokens)[\"']?\s*[:=]\s*$", prefix)
        if numeric_budget and re.fullmatch(r"\d+\s*[,)]?\s*", value):
            return match.group(0)
        return prefix + "[REDACTED]"

    text = re.sub(
        r"(?im)((?:[A-Z_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z_]*)[\"']?\s*[:=]\s*)([^\r\n]+)",
        mask_assignment, text,
    )
    text = re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|\Z)",
        "[REDACTED_PRIVATE_KEY]", text,
    )
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
