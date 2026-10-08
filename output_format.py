"""AI 출력을 다듬고 길이와 PR 템플릿을 보장한다."""


def one_line(value: object) -> str:
    """문자열만 받아 줄바꿈과 연속된 공백을 정리한다."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip("`# ")


def get_items(draft: dict, key: str, fallback: str) -> list[str]:
    """배열에서 비어 있지 않은 항목을 꺼내고 부족하면 안내를 보충한다."""
    values = draft.get(key, [])
    if not isinstance(values, list):
        values = []
    items = []
    for value in values:
        item = one_line(value).lstrip("-* ")
        if item:
            items.append(item)
    return items or [fallback]


def format_draft(command: str, draft: dict) -> tuple[str, list[str]]:
    """복사용 완성 텍스트와 보정 내용을 반환한다. 재생성하지 않는다."""
    notices = []
    title = one_line(draft.get("title"))
    if not title:
        raise ValueError("AI 출력에 비어 있지 않은 제목이 없습니다.")
    limit = 72 if command == "commit" else 80
    if len(title) > limit:
        title = title[:limit - 1].rstrip() + "…"
        notices.append(f"제목을 {limit}자 이내로 줄였습니다. 의미를 확인해 주세요.")
    if command == "commit":
        if len(title) > 50:
            notices.append("커밋 제목은 50자 이내를 권장합니다.")
        items = get_items(draft, "changes", "핵심 변경: " + title)[:2]
        body = "\n".join("- " + item for item in items)
        return title + "\n\n" + body, notices
    sections = [
        ("Why", "why", "변경 배경은 미확인입니다. 작성자가 보충해 주세요."),
        ("What", "what", "변경 내용의 세부 사항은 diff를 확인해 주세요."),
        ("How to Test", "how_to_test", "테스트 미실행입니다. 대상 기능을 검증해 주세요."),
    ]
    body_parts = []
    for heading, key, fallback in sections:
        items = get_items(draft, key, fallback)
        if items == [fallback]:
            notices.append(heading + "의 부족한 항목을 안내문으로 보충했습니다.")
        body_parts.append("## " + heading + "\n" + "\n".join("- " + item for item in items))
    body = "\n\n".join(body_parts)
    return title + "\n\n" + body, notices
