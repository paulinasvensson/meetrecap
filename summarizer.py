"""
Core meetrecap logic: turns messy meeting notes into a clean summary and a
list of action items, using lightweight, dependency-free NLP heuristics
(word-frequency sentence scoring + pattern-based action-item extraction).
"""

import re

STOPWORDS = set(
    """
    a an the and or but if then so to of in on at for with as by from is are
    was were be been being this that these those it its it's we you they he
    she i our your their will would can could should shall may might must
    not no yes just also very really about into over under again further
    once here there when where why how all any both each few more most
    other some such only own same than too s t don now let ok well um okay
    meeting notes today discussed talked said going need needs
    """.split()
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
WORD_RE = re.compile(r"[A-Za-z']+")

ACTION_KEYWORDS = re.compile(
    r"\b(will|need to|needs to|should|must|action item|todo|to-do|follow up|"
    r"assign|responsible for|by (monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|eod|tomorrow|next week|end of day))\b",
    re.IGNORECASE,
)

DEADLINE_RE = re.compile(
    r"\bby (monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"tomorrow|next week|eod|end of day|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
    re.IGNORECASE,
)

OWNER_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_]*)")
OWNER_NAME_RE = re.compile(r"\b([A-Z][a-z]+)\s+(?:will|should|needs? to|must)\b")

URGENT_RE = re.compile(r"\b(urgent|asap|critical|immediately|high priority)\b", re.IGNORECASE)


def split_sentences(text: str):
    text = text.strip()
    if not text:
        return []
    parts = [p.strip() for p in SENTENCE_SPLIT_RE.split(text) if p.strip()]
    return parts


def _word_freq(sentences):
    freq = {}
    for s in sentences:
        for w in WORD_RE.findall(s.lower()):
            if w in STOPWORDS or len(w) < 3:
                continue
            freq[w] = freq.get(w, 0) + 1
    if freq:
        maxf = max(freq.values())
        for k in freq:
            freq[k] = freq[k] / maxf
    return freq


def summarize_text(text: str, max_sentences: int = 5):
    sentences = split_sentences(text)
    if not sentences:
        return []
    freq = _word_freq(sentences)

    scored = []
    for idx, s in enumerate(sentences):
        words = WORD_RE.findall(s.lower())
        if not words:
            continue
        score = sum(freq.get(w, 0) for w in words) / len(words)
        # small boost for earlier sentences (often set context)
        score += (1.0 / (idx + 1)) * 0.05
        scored.append((idx, score, s))

    top = sorted(scored, key=lambda t: t[1], reverse=True)[:max_sentences]
    top_sorted_by_position = sorted(top, key=lambda t: t[0])
    return [s for (_, _, s) in top_sorted_by_position]


def extract_action_items(text: str, max_items: int | None = None, with_details: bool = False):
    sentences = split_sentences(text)
    items = []
    for s in sentences:
        if ACTION_KEYWORDS.search(s):
            entry = {"text": s.strip()}
            if with_details:
                owner = None
                m = OWNER_RE.search(s)
                if m:
                    owner = m.group(1)
                else:
                    m2 = OWNER_NAME_RE.search(s)
                    if m2:
                        owner = m2.group(1)
                deadline = None
                dm = DEADLINE_RE.search(s)
                if dm:
                    deadline = dm.group(1)
                priority = "high" if URGENT_RE.search(s) else "normal"
                entry.update({"owner": owner, "deadline": deadline, "priority": priority})
            items.append(entry)
        if max_items and len(items) >= max_items:
            break
    return items
