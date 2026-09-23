import re
from datetime import datetime

ACTION_KEYWORDS = [
    "will", "should", "need to", "needs to", "must", "todo", "to-do",
    "action item", "follow up", "follow-up", "plan to", "going to",
    "responsible for", "owns", "due"
]

DATE_PATTERNS = [
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b",
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bnext\s+week\b",
    r"\btomorrow\b",
    r"\bend of (?:day|week|month)\b",
    r"\bEOD\b",
    r"\bEOW\b",
]

MENTION_PATTERN = r"@([A-Za-z][A-Za-z0-9_\.]*)"
NAME_PATTERN = r"\b([A-Z][a-z]+)\s+(?:will|should|to|needs|must|is|owns)\b"


def _split_sentences(text):
    text = text.replace("\r", "")
    # split on newlines, bullets, and sentence terminators
    raw = re.split(r"(?<=[.!?])\s+|\n+|(?:^|\n)[\-\*\u2022]\s*", text)
    return [s.strip(" -\t") for s in raw if s and s.strip(" -\t")]


def free_summarize(text: str):
    """Free tier: simple extractive summary, capped in size."""
    sentences = _split_sentences(text)
    if not sentences:
        return {"summary": "", "line_count": 0}
    # take up to 3 longest/most informative sentences as a quick summary
    ranked = sorted(sentences, key=len, reverse=True)[:3]
    summary = " ".join(ranked)
    if len(summary) > 400:
        summary = summary[:400].rsplit(" ", 1)[0] + "..."
    return {
        "summary": summary,
        "line_count": len(sentences),
        "note": "Free preview: top 3 sentences only. Unlock full recap with a license key.",
    }


def full_recap(text: str):
    """Paid tier: full clean summary + action items with owners/dates + decisions."""
    sentences = _split_sentences(text)

    action_items = []
    decisions = []

    for s in sentences:
        low = s.lower()
        is_action = any(k in low for k in ACTION_KEYWORDS)
        is_decision = any(w in low for w in ["decided", "agreed", "concluded", "approved", "resolved"])

        owner = None
        mention = re.search(MENTION_PATTERN, s)
        if mention:
            owner = mention.group(1)
        else:
            name_match = re.search(NAME_PATTERN, s)
            if name_match:
                owner = name_match.group(1)

        due = None
        for pat in DATE_PATTERNS:
            m = re.search(pat, s, re.IGNORECASE)
            if m:
                due = m.group(0)
                break

        if is_action:
            action_items.append({
                "task": s,
                "owner": owner or "Unassigned",
                "due": due or "No date mentioned",
            })
        elif is_decision:
            decisions.append(s)

    # Build a clean overall summary from non-action, non-decision sentences + key ones
    remainder = [s for s in sentences if s not in [d for d in decisions] and s not in [a["task"] for a in action_items]]
    key_sentences = sorted(remainder, key=len, reverse=True)[:4] if remainder else sentences[:4]
    clean_summary = " ".join(key_sentences)

    return {
        "clean_summary": clean_summary or "No summary could be generated.",
        "decisions": decisions,
        "action_items": action_items,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_lines_analyzed": len(sentences),
    }
