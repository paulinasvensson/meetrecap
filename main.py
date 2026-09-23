import re
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from entitlements import require_pro

app = FastAPI(title="meetrecap")


class NotesPayload(BaseModel):
    notes: str


def _sentences(text: str):
    text = re.sub(r"\s+", " ", text).strip()
    # split on sentence-ish boundaries and bullet lines
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip(" -•\t") for s in raw if s.strip(" -•\t")]


def make_summary(notes: str) -> list[str]:
    """Free feature: turn messy notes into a clean bullet-point summary."""
    sents = _sentences(notes)
    if not sents:
        return []
    # keep sentences with reasonable length, dedupe, cap at 6 bullets
    seen = set()
    bullets = []
    for s in sents:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        if len(s) < 4:
            continue
        bullets.append(s if s.endswith((".", "!", "?")) else s + ".")
        if len(bullets) >= 6:
            break
    return bullets


ACTION_VERBS = [
    "will", "should", "must", "need to", "needs to", "to do", "action",
    "follow up", "follow-up", "send", "schedule", "review", "prepare",
    "create", "update", "finalize", "finalise", "contact", "email",
    "call", "complete", "fix", "investigate", "share", "draft", "assign",
]

OWNER_RE = re.compile(r"\b([A-Z][a-z]+)\s+(?:will|to|should|needs to|must)\b")
DEADLINE_RE = re.compile(
    r"\b(by\s+\w+day|by\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?|by\s+(?:end of|EOD|EOW)\s*\w*|"
    r"tomorrow|today|next week|this week|by\s+\w+\s+\d{1,2}(?:st|nd|rd|th)?)\b",
    re.IGNORECASE,
)


def extract_action_items(notes: str) -> list[dict]:
    """Paid feature: pull out action items with likely owner + deadline."""
    sents = _sentences(notes)
    items = []
    for s in sents:
        low = s.lower()
        if any(v in low for v in ACTION_VERBS):
            owner_match = OWNER_RE.search(s)
            deadline_match = DEADLINE_RE.search(s)
            items.append({
                "task": s if s.endswith((".", "!", "?")) else s + ".",
                "owner": owner_match.group(1) if owner_match else "Unassigned",
                "deadline": deadline_match.group(0) if deadline_match else "No deadline found",
            })
    return items


@app.post("/api/summarize")
def summarize(payload: NotesPayload):
    return {"summary": make_summary(payload.notes)}


@app.post("/api/action-items")
def action_items(payload: NotesPayload, _=Depends(require_pro)):
    return {"action_items": extract_action_items(payload.notes)}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>meetrecap</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 font-sans text-slate-800">
<div class="max-w-3xl mx-auto p-4">

  <div class="mb-3">
    <h1 class="text-xl font-semibold text-slate-900">meetrecap</h1>
    <p class="text-sm text-slate-500">Paste messy meeting notes. Get a clean summary free, unlock structured action items with a license.</p>
  </div>

  <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-4 mb-3">
    <textarea id="notes" rows="5"
      class="w-full rounded-lg border border-slate-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      placeholder="e.g. Sarah will send the proposal by Friday. We need to review the budget. John to schedule a follow-up call next week..."></textarea>

    <div class="flex flex-wrap gap-2 mt-3">
      <button id="summarizeBtn"
        class="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
        Summarize (free)
      </button>
      <button id="actionsBtn"
        class="bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
        Extract Action Items (pro)
      </button>
    </div>
  </div>

  <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-4 mb-3">
    <label class="block text-xs font-medium text-slate-500 mb-1">License key (for Pro features)</label>
    <input id="licenseKey" type="text" placeholder="Paste your license key"
      class="w-full rounded-lg border border-slate-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
  </div>

  <div id="result" class="bg-white border border-slate-200 rounded-lg shadow-sm p-4 min-h-[80px] text-sm">
    <p class="text-slate-400">Results will appear here.</p>
  </div>

</div>

<script>
const licenseInput = document.getElementById('licenseKey');
licenseInput.value = localStorage.getItem('meetrecap_license') || '';
licenseInput.addEventListener('input', () => {
  localStorage.setItem('meetrecap_license', licenseInput.value.trim());
});

const resultBox = document.getElementById('result');

function renderList(title, items, renderItem) {
  if (!items || items.length === 0) {
    resultBox.innerHTML = `<p class="text-slate-400">No ${title.toLowerCase()} found. Try adding more detail to your notes.</p>`;
    return;
  }
  const html = `
    <h2 class="text-sm font-semibold text-slate-900 mb-2">${title}</h2>
    <ul class="space-y-2">
      ${items.map(renderItem).join('')}
    </ul>
  `;
  resultBox.innerHTML = html;
}

document.getElementById('summarizeBtn').addEventListener('click', async () => {
  const notes = document.getElementById('notes').value.trim();
  if (!notes) { resultBox.innerHTML = '<p class="text-red-500">Paste some notes first.</p>'; return; }
  resultBox.innerHTML = '<p class="text-slate-400">Summarizing...</p>';
  try {
    const res = await fetch('/api/summarize', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({notes})
    });
    const data = await res.json();
    renderList('Summary', data.summary, (s) => `<li class="flex gap-2"><span class="text-indigo-500">•</span><span>${s}</span></li>`);
  } catch (e) {
    resultBox.innerHTML = '<p class="text-red-500">Something went wrong. Try again.</p>';
  }
});

document.getElementById('actionsBtn').addEventListener('click', async () => {
  const notes = document.getElementById('notes').value.trim();
  if (!notes) { resultBox.innerHTML = '<p class="text-red-500">Paste some notes first.</p>'; return; }
  const key = localStorage.getItem('meetrecap_license') || '';
  resultBox.innerHTML = '<p class="text-slate-400">Extracting action items...</p>';
  try {
    const res = await fetch('/api/action-items', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-License-Key': key},
      body: JSON.stringify({notes})
    });
    if (res.status === 402) {
      resultBox.innerHTML = `
        <div class="border border-amber-300 bg-amber-50 rounded-lg p-3">
          <p class="font-medium text-amber-800">Pro license required</p>
          <p class="text-amber-700 mt-1">Enter a valid license key above to unlock action item extraction with owners and deadlines.</p>
        </div>`;
      return;
    }
    const data = await res.json();
    renderList('Action Items', data.action_items, (item) => `
      <li class="border border-slate-100 rounded-lg p-2 bg-slate-50">
        <p class="text-slate-900">${item.task}</p>
        <p class="text-xs text-slate-500 mt-1">Owner: <span class="font-medium text-slate-700">${item.owner}</span> · Deadline: <span class="font-medium text-slate-700">${item.deadline}</span></p>
      </li>
    `);
  } catch (e) {
    resultBox.innerHTML = '<p class="text-red-500">Something went wrong. Try again.</p>';
  }
});
</script>
</body>
</html>
"""
