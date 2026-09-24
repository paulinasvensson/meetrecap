import re
from datetime import datetime

ACTION_KEYWORDS = [
    "will", "need to", "needs to", "todo", "to-do", "action item",
    "should", "must", "follow up", "follow-up", "by friday", "by monday",
    "let's", "lets", "plan to", "going to",
]

DATE_HINTS = re.compile(
    r"\b(by\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tomorrow|eod|eow|next week|\d{1,2}/\d{1,2}))\b",
    re.IGNORECASE,
)

ASSIGNEE_PATTERNS = [
    re.compile(r"@(\w+)"),
    re.compile(r"^([A-Z][a-z]+):"),
    re.compile(r"\b([A-Z][a-z]+)\s+(?:will|to|should|needs to|needs)\b"),
]


def _clean_lines(notes: str):
    raw = [l.strip(" -•\t") for l in notes.splitlines()]
    return [l for l in raw if l]


def _is_action(line: str) -> bool:
    low = line.lower()
    return any(kw in low for kw in ACTION_KEYWORDS)


def _find_assignee(line: str):
    for pat in ASSIGNEE_PATTERNS:
        m = pat.search(line)
        if m:
            return m.group(1)
    return None


def _find_due(line: str):
    m = DATE_HINTS.search(line)
    return m.group(1).title() if m else None


def basic_summary(notes: str, max_lines: int = 4):
    """Free preview: short summary, no action-item structuring."""
    lines = _clean_lines(notes)
    if not lines:
        return {"summary": "No notes provided.", "preview_lines": 0}
    preview = lines[:max_lines]
    summary = " ".join(preview)
    if len(summary) > 320:
        summary = summary[:320].rsplit(" ", 1)[0] + "..."
    return {
        "summary": summary,
        "total_lines": len(lines),
        "shown_lines": len(preview),
        "truncated": len(lines) > max_lines,
    }


def full_recap(notes: str):
    """Paid feature: full summary + structured action items."""
    lines = _clean_lines(notes)
    if not lines:
        return {"summary": "No notes provided.", "action_items": []}

    summary_lines = lines[:12]
    summary = " ".join(summary_lines)
    if len(summary) > 900:
        summary = summary[:900].rsplit(" ", 1)[0] + "..."

    action_items = []
    for line in lines:
        if _is_action(line):
            action_items.append({
                "task": line,
                "assignee": _find_assignee(line) or "Unassigned",
                "due": _find_due(line) or "No date specified",
            })

    return {
        "summary": summary,
        "total_lines": len(lines),
        "action_items": action_items,
        "action_item_count": len(action_items),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
