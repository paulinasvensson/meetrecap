import re
from collections import Counter

STOPWORDS = set("""
a an the and or but if then so of to in on at for with by from as is are was were
be been being this that these those it its it's we you they he she i our your their
about into over under again further not no nor can will just should now
""".split())

ACTION_KEYWORDS = [
    "will", "need to", "needs to", "should", "must", "todo", "to-do", "action item",
    "action:", "follow up", "follow-up", "by friday", "by monday", "assign", "owns",
    "responsible", "due"
]

DATE_PATTERN = re.compile(
    r"\b(by\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tomorrow|next week|end of week|eow|\d{1,2}/\d{1,2}(?:/\d{2,4})?|"
    r"\d{4}-\d{2}-\d{2})\b", re.IGNORECASE
)

OWNER_PATTERN = re.compile(r"@([A-Za-z][A-Za-z0-9_\-]*)|\b([A-Z][a-z]+)\s+will\b")


def _split_sentences(text):
    text = text.replace("\n", ". ")
    parts = re.split(r"(?<=[.!?])\s+|\n+|•|-\s{1,2}", text)
    return [p.strip(" .-\t") for p in parts if p.strip(" .-\t")]


def quick_summary(text, max_bullets=3):
    """Simple frequency-based extractive summary - free tier."""
    sentences = _split_sentences(text)
    if not sentences:
        return []

    words = re.findall(r"[a-zA-Z']+", text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS and len(w) > 2)

    scored = []
    for s in sentences:
        s_words = re.findall(r"[a-zA-Z']+", s.lower())
        score = sum(freq.get(w, 0) for w in s_words)
        norm = score / (len(s_words) + 1)
        scored.append((norm, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_bullets]]
    # preserve original order
    ordered = [s for s in sentences if s in top]
    return ordered[:max_bullets]


def full_summary(text, max_bullets=6):
    return quick_summary(text, max_bullets=max_bullets)


def extract_action_items(text):
    """Heuristic action-item extraction - pro tier."""
    sentences = _split_sentences(text)
    items = []
    for s in sentences:
        lower = s.lower()
        if any(kw in lower for kw in ACTION_KEYWORDS):
            date_match = DATE_PATTERN.search(s)
            owner_match = OWNER_PATTERN.search(s)
            owner = None
            if owner_match:
                owner = owner_match.group(1) or owner_match.group(2)
            items.append({
                "task": s.strip(),
                "owner": owner,
                "due": date_match.group(0) if date_match else None,
            })
    return items
