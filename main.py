import re
from collections import Counter
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from entitlements import require_pro

app = FastAPI(title="meetrecap")


class NotesIn(BaseModel):
    notes: str


ACTION_KEYWORDS = [
    "will", "should", "need to", "needs to", "todo", "to do",
    "action item", "follow up", "follow-up", "must", "plan to",
    "going to", "assign", "next step",
]

STOPWORDS = set("""
a an the and or but if then so of to in on for with at by from as is
are was were be been being this that it its our we they you he she
i me my your their his her not no yes okay ok just also into over
about up down out than into more most some any all can could would
""".split())


def split_sentences(text: str):
    text = text.replace("\n", ". ")
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def extract_action_items(text: str):
    lines = re.split(r"[\n.]+", text)
    items = []
    for line in lines:
        clean = line.strip(" -*\t")
        if not clean:
            continue
        low = clean.lower()
        if any(kw in low for kw in ACTION_KEYWORDS):
            items.append(clean)
    return items


def naive_summary(text: str, max_sentences: int = 4):
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return sentences
    words = re.findall(r"[a-zA-Z']+", text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS)
    scored = []
    for s in sentences:
        s_words = re.findall(r"[a-zA-Z']+", s.lower())
        score = sum(freq.get(w, 0) for w in s_words)
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_sentences]]
    # preserve original order
    return [s for s in sentences if s in top]


DEADLINE_RE = re.compile(
    r"\b(by|before|due)\s+([A-Za-z]+\s?\d{0,4}|\d{1,2}/\d{1,2}(/\d{2,4})?|next\s+\w+|tomorrow|eod|end of (day|week))",
    re.IGNORECASE,
)
ASSIGNEE_RE = re.compile(r"@(\w+)|\b([A-Z][a-z]+)\s+will\b")


def structured_action_items(text: str):
    raw_items = extract_action_items(text)
    structured = []
    for item in raw_items:
        deadline_match = DEADLINE_RE.search(item)
        deadline = deadline_match.group(0) if deadline_match else None
        assignee_match = ASSIGNEE_RE.search(item)
        assignee = None
        if assignee_match:
            assignee = assignee_match.group(1) or assignee_match.group(2)
        structured.append({
            "task": item,
            "assignee": assignee,
            "deadline": deadline,
        })
    return structured


def key_topics(text: str, top_n: int = 6):
    words = re.findall(r"[a-zA-Z']{4,}", text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS)
    return [w for w, _ in freq.most_common(top_n)]


def extract_decisions(text: str):
    lines = re.split(r"[\n.]+", text)
    decisions = []
    for line in lines:
        clean = line.strip(" -*\t")
        low = clean.lower()
        if any(kw in low for kw in ["decided", "agreed", "decision", "we will go with", "approved"]):
            decisions.append(clean)
    return decisions


@app.post("/api/summarize")
def summarize_free(payload: NotesIn):
    """Free tier: quick summary + basic action item detection."""
    notes = payload.notes or ""
    summary = naive_summary(notes)
    actions = extract_action_items(notes)
    return {
        "summary": summary,
        "action_items": actions[:5],
        "note": "Free quick recap. Unlock Pro Recap for owners, deadlines, decisions & topics.",
    }


@app.post("/api/summarize/pro")
def summarize_pro(payload: NotesIn, _=Depends(require_pro)):
    """Paid tier: full structured recap."""
    notes = payload.notes or ""
    summary = naive_summary(notes, max_sentences=6)
    actions = structured_action_items(notes)
    decisions = extract_decisions(notes)
    topics = key_topics(notes)
    return {
        "summary": summary,
        "action_items": actions,
        "decisions": decisions,
        "key_topics": topics,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>meetrecap</title>
<style>
  body { font-family: -apple-system, Arial, sans-serif; max-width: 820px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }
  h1 { margin-bottom: 4px; }
  .sub { color: #666; margin-top: 0; }
  textarea { width: 100%; height: 200px; font-size: 14px; padding: 10px; box-sizing: border-box; }
  .row { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
  button { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
  .free-btn { background: #2563eb; color: white; }
  .pro-btn { background: #16a34a; color: white; }
  .license-box { margin: 20px 0; padding: 12px; background: #f5f5f5; border-radius: 8px; }
  .license-box input { padding: 8px; width: 260px; }
  .result { margin-top: 20px; padding: 16px; background: #fafafa; border: 1px solid #eee; border-radius: 8px; white-space: pre-wrap; }
  .error { color: #b91c1c; font-weight: bold; }
  ul { margin: 4px 0; }
  code { background: #eee; padding: 2px 4px; border-radius: 4px; }
</style>
</head>
<body>
<h1>meetrecap</h1>
<p class="sub">Turn messy meeting notes into clean summaries and action items.</p>

<div class="license-box">
  <label>License key (for Pro Recap): </label><br/>
  <input id="licenseKey" type="text" placeholder="e.g. DEMO-PRO-KEY" />
  <button onclick="saveKey()">Save</button>
  <span id="keyStatus"></span>
</div>

<textarea id="notes" placeholder="Paste your messy meeting notes here..."></textarea>

<div class="row">
  <button class="free-btn" onclick="runFree()">Quick Summary (Free)</button>
  <button class="pro-btn" onclick="runPro()">Pro Recap (Paid)</button>
</div>

<div id="result" class="result" style="display:none;"></div>

<script>
function saveKey() {
  const key = document.getElementById('licenseKey').value.trim();
  localStorage.setItem('meetrecap_license', key);
  document.getElementById('keyStatus').innerText = key ? "Saved." : "";
}

window.onload = function() {
  const saved = localStorage.getItem('meetrecap_license');
  if (saved) document.getElementById('licenseKey').value = saved;
};

function showResult(html) {
  const el = document.getElementById('result');
  el.style.display = 'block';
  el.innerHTML = html;
}

async function runFree() {
  const notes = document.getElementById('notes').value;
  showResult("Working...");
  try {
    const res = await fetch('/api/summarize', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({notes})
    });
    const data = await res.json();
    let html = "<h3>Summary</h3><ul>" + data.summary.map(s => `<li>${s}</li>`).join('') + "</ul>";
    html += "<h3>Action Items (basic)</h3>";
    html += data.action_items.length
      ? "<ul>" + data.action_items.map(a => `<li>${a}</li>`).join('') + "</ul>"
      : "<p>None detected.</p>";
    html += `<p><em>${data.note}</em></p>`;
    showResult(html);
  } catch (e) {
    showResult('<span class="error">Something went wrong. Try again.</span>');
  }
}

async function runPro() {
  const notes = document.getElementById('notes').value;
  const key = localStorage.getItem('meetrecap_license') || '';
  showResult("Working...");
  try {
    const res = await fetch('/api/summarize/pro', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-License-Key': key},
      body: JSON.stringify({notes})
    });
    if (res.status === 402) {
      showResult('<span class="error">This is a Pro feature. Please enter a valid license key above (try DEMO-PRO-KEY) and click Save, then try again.</span>');
      return;
    }
    const data = await res.json();
    let html = "<h3>Pro Summary</h3><ul>" + data.summary.map(s => `<li>${s}</li>`).join('') + "</ul>";

    html += "<h3>Structured Action Items</h3>";
    html += data.action_items.length
      ? "<ul>" + data.action_items.map(a =>
          `<li>${a.task} ${a.assignee ? '<b>[Owner: ' + a.assignee + ']</b>' : ''} ${a.deadline ? '<b>[Due: ' + a.deadline + ']</b>' : ''}</li>`
        ).join('') + "</ul>"
      : "<p>None detected.</p>";

    html += "<h3>Decisions</h3>";
    html += data.decisions.length
      ? "<ul>" + data.decisions.map(d => `<li>${d}</li>`).join('') + "</ul>"
      : "<p>None detected.</p>";

    html += "<h3>Key Topics</h3><p>" + (data.key_topics.join(', ') || 'None') + "</p>";
    showResult(html);
  } catch (e) {
    showResult('<span class="error">Something went wrong. Try again.</span>');
  }
}
</script>
</body>
</html>
"""
