import re
from collections import Counter
from datetime import datetime

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from entitlements import require_pro, generate_demo_key

app = FastAPI(title="meetrecap")
templates = Jinja2Templates(directory="templates")


class NotesIn(BaseModel):
    notes: str


STOP_PHRASES = {"um", "uh", "like", "you know", "sort of", "kind of", "basically"}

ACTION_VERBS = [
    "will", "should", "need to", "needs to", "must", "going to",
    "let's", "let us", "plan to", "have to", "has to", "action item",
    "follow up", "follow-up", "todo", "to-do",
]

OWNER_PATTERN = re.compile(
    r"\b([A-Z][a-z]+)\s+(?:will|should|needs to|to|is going to|has to)\b"
)

DATE_PATTERN = re.compile(
    r"\b(by\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"tomorrow|today|next week|eod|end of day|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
    re.IGNORECASE,
)


def clean_line(line: str) -> str:
    text = line.strip(" -*\t\u2022")
    for phrase in STOP_PHRASES:
        text = re.sub(rf"\b{re.escape(phrase)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        text = text[0].upper() + text[1:]
        if not text.endswith((".", "!", "?")):
            text += "."
    return text


def split_lines(notes: str):
    raw = re.split(r"[\n\r]+|(?<=[.!?])\s{2,}", notes)
    lines = [clean_line(l) for l in raw if l.strip()]
    return [l for l in lines if len(l) > 3]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "demo_key": generate_demo_key()}
    )


@app.post("/api/summarize")
async def summarize(payload: NotesIn):
    """FREE: turn messy notes into a clean, deduped bullet summary."""
    lines = split_lines(payload.notes)

    seen = set()
    deduped = []
    for l in lines:
        key = l.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(l)

    words = re.findall(r"[a-zA-Z]{4,}", payload.notes.lower())
    common = [w for w, _ in Counter(words).most_common(5)]

    max_free_bullets = 6
    summary = deduped[:max_free_bullets]
    truncated = len(deduped) > max_free_bullets

    return {
        "summary": summary,
        "key_topics": common,
        "truncated": truncated,
        "total_lines_found": len(deduped),
    }


@app.post("/api/extract-actions")
async def extract_actions(payload: NotesIn, _license=Depends(require_pro)):
    """PAID: full clean summary + structured action items with owner/due date/priority."""
    lines = split_lines(payload.notes)

    seen = set()
    deduped = []
    for l in lines:
        key = l.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(l)

    action_items = []
    for line in deduped:
        lower = line.lower()
        if any(verb in lower for verb in ACTION_VERBS):
            owner_match = OWNER_PATTERN.search(line)
            date_match = DATE_PATTERN.search(line)
            owner = owner_match.group(1) if owner_match else "Unassigned"
            due = date_match.group(0) if date_match else "No date given"

            priority = "High" if any(
                w in lower for w in ["urgent", "asap", "critical", "today", "eod"]
            ) else "Medium" if date_match else "Low"

            action_items.append({
                "task": line,
                "owner": owner,
                "due": due,
                "priority": priority,
            })

    non_action_summary = [l for l in deduped if l not in [a["task"] for a in action_items]]

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "clean_summary": non_action_summary,
        "action_items": action_items,
        "total_action_items": len(action_items),
    }
