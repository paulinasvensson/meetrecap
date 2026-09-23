"""
Core summarization logic for MeetRecap.

Uses frequency-based extractive summarization (no external API required),
plus keyword-driven extraction of action items and decisions. This keeps
the MVP runnable offline while still doing real analytical work.
"""
import re
from collections import Counter
from typing import List, Dict

STOPWORDS = set("""
a an the and or but if then so to of in on for with at by from as is are was
were be been being this that these those it its it's he she they we you i
your our their his her them us not no do does did done can could will would
should shall may might must about into over under again further once here
there when where why how all any both each few more most other some such
only own same than too very s t just don should've now
""".split())

ACTION_PATTERNS = [
    r"\bwill\b", r"\bshould\b", r"\bmust\b", r"\bneed(?:s)? to\b",
    r"\baction item\b", r"\btodo\b", r"\bto-do\b", r"\bfollow up\b",
    r"\bassign(?:ed)? to\b", r"\bby (?:monday|tuesday|wednesday|thursday|friday|next week|eod|end of day)\b",
]
DECISION_PATTERNS = [
    r"\bdecided\b", r"\bagreed\b", r"\bapproved\b", r"\bfinaliz(?:ed|e)\b",
    r"\bconclusion\b", r"\bresolved\b",
]

OWNER_PATTERN = re.compile(r"@([A-Za-z][\w]*)")
NAME_PREFIX_PATTERN = re.compile(r"^\s*([A-Z][a-z]+)\s*:")


def _split_sentences(text: str) -> List[str]:
    # naive sentence splitter that also respects line breaks (bullet notes)
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [c.strip() for c in chunks if c.strip()]


def _word_frequencies(sentences: List[str]) -> Counter:
    freq = Counter()
    for s in sentences:
        for w in re.findall(r"[a-zA-Z']+", s.lower()):
            if w not in STOPWORDS:
                freq[w] += 1
    return freq


def _score_sentences(sentences: List[str], freq: Counter) -> Dict[int, float]:
    scores = {}
    for i, s in enumerate(sentences):
        words = re.findall(r"[a-zA-Z']+", s.lower())
        if not words:
            continue
        score = sum(freq.get(w, 0) for w in words) / len(words)
        scores[i] = score
    return scores


def basic_summary(text: str, max_sentences: int = 3) -> Dict:
    """Free-tier: short extractive summary, no action items / decisions."""
    sentences = _split_sentences(text)
    if not sentences:
        return {"summary": "", "sentence_count": 0}

    freq = _word_frequencies(sentences)
    scores = _score_sentences(sentences, freq)

    top_idx = sorted(sorted(scores, key=lambda i: scores[i], reverse=True)[:max_sentences])
    summary = " ".join(sentences[i] for i in top_idx)

    return {
        "summary": summary,
        "sentence_count": len(sentences),
        "note": "This is a limited preview. Upgrade for full recap with action items and decisions.",
    }


def _extract_matching(sentences: List[str], patterns: List[str]) -> List[Dict]:
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    results = []
    for s in sentences:
        if any(p.search(s) for p in compiled):
            owner_match = OWNER_PATTERN.search(s)
            name_match = NAME_PREFIX_PATTERN.match(s)
            owner = owner_match.group(1) if owner_match else (name_match.group(1) if name_match else None)
            results.append({"text": s, "owner": owner})
    return results


def full_recap(text: str, max_sentences: int = 6) -> Dict:
    """Pro-tier: full recap with summary, key points, action items, decisions."""
    sentences = _split_sentences(text)
    if not sentences:
        return {
            "summary": "",
            "key_points": [],
            "action_items": [],
            "decisions": [],
            "sentence_count": 0,
        }

    freq = _word_frequencies(sentences)
    scores = _score_sentences(sentences, freq)

    ranked = sorted(scores, key=lambda i: scores[i], reverse=True)
    top_idx = sorted(ranked[:max_sentences])
    summary = " ".join(sentences[i] for i in top_idx)

    key_points = [sentences[i] for i in top_idx]
    action_items = _extract_matching(sentences, ACTION_PATTERNS)
    decisions = _extract_matching(sentences, DECISION_PATTERNS)

    top_keywords = [w for w, _ in freq.most_common(8)]

    return {
        "summary": summary,
        "key_points": key_points,
        "action_items": action_items,
        "decisions": decisions,
        "top_keywords": top_keywords,
        "sentence_count": len(sentences),
    }
