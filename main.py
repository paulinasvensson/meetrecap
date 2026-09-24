from fastapi import FastAPI, Depends, Body
from fastapi.responses import HTMLResponse, JSONResponse
from entitlements import require_pro
import summarizer

app = FastAPI(title="meetrecap")


@app.post("/api/quick-summary")
async def quick_summary(payload: dict = Body(...)):
    notes = payload.get("notes", "")
    if not notes.strip():
        return JSONResponse({"error": "Please paste some meeting notes."}, status_code=400)
    bullets = summarizer.quick_summary(notes, max_bullets=3)
    action_count = len(summarizer.extract_action_items(notes))
    return {
        "summary": bullets,
        "action_item_teaser": f"{action_count} potential action item(s) detected. Upgrade to extract owners & due dates."
        if action_count else "No obvious action items detected."
    }


@app.post("/api/full-recap")
async def full_recap(payload: dict = Body(...), _lic=Depends(require_pro)):
    notes = payload.get("notes", "")
    if not notes.strip():
        return JSONResponse({"error": "Please paste some meeting notes."}, status_code=400)
    summary = summarizer.full_summary(notes, max_bullets=6)
    actions = summarizer.extract_action_items(notes)
    return {"summary": summary, "action_items": actions}


@app.get("/", response_class=HTMLResponse)
async def index():
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
<body class="bg-white text-slate-800 font-sans">
<div class="max-w-2xl mx-auto p-4">

  <div class="mb-4">
    <h1 class="text-xl font-semibold text-slate-900">meetrecap</h1>
    <p class="text-sm text-slate-500">Paste messy meeting notes. Get a clean summary and action items.</p>
  </div>

  <textarea id="notes" rows="5"
    class="w-full rounded-lg border border-slate-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
    placeholder="Paste your raw meeting notes here..."></textarea>

  <div class="flex flex-wrap gap-2 mt-3">
    <button id="quickBtn"
      class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition">
      Quick Summary (Free)
    </button>
    <button id="proBtn"
      class="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 transition">
      Full Recap + Action Items (Pro)
    </button>
  </div>

  <div class="mt-4">
    <label class="block text-xs font-medium text-slate-500 mb-1">License Key</label>
    <input id="licenseKey" type="text" placeholder="Enter your license key"
      class="w-full rounded-lg border border-slate-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
  </div>

  <div id="result" class="mt-4 text-sm"></div>

</div>

<script>
const licenseInput = document.getElementById('licenseKey');
licenseInput.value = localStorage.getItem('meetrecap_license') || '';
licenseInput.addEventListener('input', () => {
  localStorage.setItem('meetrecap_license', licenseInput.value.trim());
});

const resultDiv = document.getElementById('result');

function renderError(msg) {
  resultDiv.innerHTML = `<div class="rounded-lg border border-red-200 bg-red-50 text-red-700 p-3">${msg}</div>`;
}

function renderSummary(title, bullets, extra) {
  let html = `<div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
    <h2 class="font-semibold text-slate-900 mb-2">${title}</h2>
    <ul class="list-disc pl-5 space-y-1">`;
  bullets.forEach(b => html += `<li>${b}</li>`);
  html += `</ul>`;
  if (extra) html += `<div class="mt-2 text-slate-600">${extra}</div>`;
  html += `</div>`;
  resultDiv.innerHTML = html;
}

function renderFull(summary, actions) {
  let html = `<div class="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
    <div>
      <h2 class="font-semibold text-slate-900 mb-2">Summary</h2>
      <ul class="list-disc pl-5 space-y-1">`;
  summary.forEach(b => html += `<li>${b}</li>`);
  html += `</ul></div><div>
      <h2 class="font-semibold text-slate-900 mb-2">Action Items</h2>`;
  if (actions.length === 0) {
    html += `<p class="text-slate-500">No action items detected.</p>`;
  } else {
    html += `<ul class="space-y-1">`;
    actions.forEach(a => {
      html += `<li class="flex flex-wrap gap-2 items-center">
        <span class="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 text-xs font-medium">${a.owner || 'Unassigned'}</span>
        <span>${a.task}</span>
        ${a.due ? `<span class="px-2 py-0.5 rounded bg-amber-100 text-amber-700 text-xs">${a.due}</span>` : ''}
      </li>`;
    });
    html += `</ul>`;
  }
  html += `</div></div>`;
  resultDiv.innerHTML = html;
}

document.getElementById('quickBtn').addEventListener('click', async () => {
  const notes = document.getElementById('notes').value;
  resultDiv.innerHTML = `<p class="text-slate-400">Summarizing...</p>`;
  const res = await fetch('/api/quick-summary', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({notes})
  });
  const data = await res.json();
  if (!res.ok) { renderError(data.error || 'Something went wrong.'); return; }
  renderSummary('Quick Summary', data.summary, data.action_item_teaser);
});

document.getElementById('proBtn').addEventListener('click', async () => {
  const notes = document.getElementById('notes').value;
  const key = localStorage.getItem('meetrecap_license') || '';
  resultDiv.innerHTML = `<p class="text-slate-400">Generating full recap...</p>`;
  const res = await fetch('/api/full-recap', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-License-Key': key},
    body: JSON.stringify({notes})
  });
  const data = await res.json();
  if (res.status === 402) {
    renderError(data.detail || 'This feature requires a valid license key. Please purchase a plan and enter your key above.');
    return;
  }
  if (!res.ok) { renderError(data.error || 'Something went wrong.'); return; }
  renderFull(data.summary, data.action_items);
});
</script>
</body>
</html>
"""
