"""
MeetRecap MVP API.

Free tier:  POST /summarize/basic   -> short extractive summary (no login/paywall)
Paid tier:  POST /summarize/full    -> full recap with action items, decisions,
                                        key points, keywords (requires X-License-Key)
"""
from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field

from entitlements import require_pro
from summarizer import basic_summary, full_recap

app = FastAPI(
    title="MeetRecap API",
    description="AI-distilled meeting notes: fast summaries, action items, and decisions.",
    version="0.1.0",
)


class NotesInput(BaseModel):
    notes: str = Field(..., min_length=1, description="Raw meeting notes / transcript text")
    max_sentences: int = Field(3, ge=1, le=10, description="Number of sentences to include in the summary")


class FullNotesInput(BaseModel):
    notes: str = Field(..., min_length=1, description="Raw meeting notes / transcript text")
    max_sentences: int = Field(6, ge=1, le=15, description="Number of sentences to include in the summary")


@app.get("/")
def root():
    return {
        "app": "MeetRecap",
        "tiers": {
            "free": "POST /summarize/basic",
            "pro": "POST /summarize/full (requires X-License-Key header)",
        },
    }


@app.post("/summarize/basic")
def summarize_basic(payload: NotesInput):
    """Free trial capability: quick, limited summary of meeting notes."""
    return basic_summary(payload.notes, max_sentences=payload.max_sentences)


@app.post("/summarize/full")
def summarize_full(payload: FullNotesInput, license_key: str = Depends(require_pro)):
    """Paid feature: full meeting recap with summary, key points,
    action items (with owners when detectable), and decisions."""
    result = full_recap(payload.notes, max_sentences=payload.max_sentences)
    result["licensed_to"] = license_key
    return result
