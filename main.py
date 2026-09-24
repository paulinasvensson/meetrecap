from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from entitlements import require_pro
from summarizer import basic_summary, full_recap

app = FastAPI(title="meetrecap")


class NotesIn(BaseModel):
    notes: str


@app.post("/api/summarize/free")
def summarize_free(payload: NotesIn):
    return basic_summary(payload.notes)


@app.post("/api/summarize/pro")
def summarize_pro(payload: NotesIn, _=Depends(require_pro)):
    return full_recap(payload.notes)


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>meetrecap</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-800 font-sans">
<div class="max-w-3xl mx-auto p-4">

  <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
    <div class="flex items-center justify-between mb-3">
      <h1 class="text-lg font-semibold text-slate-900">meetrecap</h1>
      <span class="text-xs text-slate-400">messy notes → clean recap</span>
    </div>

    <textarea id="notes" rows="5"
      class="w-full rounded-lg border border-slate-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      placeholder="Paste your raw meeting notes here...
e.g.
- discussed Q3 roadmap
- Sarah will send the deck by Friday
- @Tom needs to follow up with legal
- team agreed to launch next week"></textarea>

    <div class="flex flex-wrap gap-2 mt-3">
      <button id="freeBtn"
        class="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium hover:bg-slate-200 transition">
        Free Preview
      </button>
      <button id="proBtn"
        class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition">
        Get Full Recap (Pro)
      </button>

      <div class="flex-1"></div>

      <input id="licenseKey" type="text" placeholder="License key"
        class="w-40 rounded-lg border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500" />
    </div>

    <div id="result" class="mt-4 text-sm text-slate-700 hidden">
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-2" id="resultBody"></div>
    </div>

    <p id="msg" class="mt-2 text-xs"></p>
  </div>
</div>

<script>
const licenseInput = document.getElementById('licenseKey');
licenseInput.value = localStorage.getItem('meetrecap_license') || '';
licenseInput.addEventListener('input', () => {
  localStorage.setItem('meetrecap_license', licenseInput.value.trim());
});

const resultDiv = document.getElementById('result');
const resultBody = document.getElementById('resultBody');
const msg = document.getElementById('msg');

function showMsg(text, isError) {
  msg.textContent = text;
  msg.className = "mt-2 text-xs " + (isError ? "text-red-600" : "text-green-600");
}

function renderFree(data) {
  resultBody.innerHTML = `
    <div><span class="font-semibold text-slate-900">Preview Summary:</span> ${data.summary}</div>
    <div class="text-xs text-slate-400">${data.shown_lines} of ${data.total_lines} lines shown${data.truncated ? ' — upgrade for full recap & action items' : ''}</div>
  `;
  resultDiv.classList.remove('hidden');
}

function renderPro(data) {
  let items = data.action_items.map(a => `
    <li class="border-l-2 border-indigo-500 pl-2">
      <div class="text-slate-800">${a.task}</div>
      <div class="text-xs text-slate-400">Assignee: ${a.assignee} · Due: ${a.due}</div>
    </li>`).join('');
  resultBody.innerHTML = `
    <div><span class="font-semibold text-slate-900">Summary:</span> ${data.summary}</div>
    <div class="font-semibold text-slate-900 mt-2">Action Items (${data.action_item_count})</div>
    <ul class="space-y-2 mt-1">${items || '<li class="text-slate-400 text-xs">No action items detected.</li>'}</ul>
  `;
  resultDiv.classList.remove('hidden');
}

document.getElementById('freeBtn').addEventListener('click', async () => {
  const notes = document.getElementById('notes').value;
  showMsg('Summarizing...', false);
  try {
    const res = await fetch('/api/summarize/free', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes })
    });
    const data = await res.json();
    if (!res.ok) { showMsg(data.detail || 'Something went wrong.', true); return; }
    renderFree(data);
    showMsg('', false);
  } catch (e) {
    showMsg('Network error.', true);
  }
});

document.getElementById('proBtn').addEventListener('click', async () => {
  const notes = document.getElementById('notes').value;
  const key = localStorage.getItem('meetrecap_license') || '';
  showMsg('Generating full recap...', false);
  try {
    const res = await fetch('/api/summarize/pro', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-License-Key': key },
      body: JSON.stringify({ notes })
    });
    if (res.status === 402) {
      showMsg('This is a Pro feature. Enter a valid license key above (get one on our pricing page) to unlock the full recap.', true);
      return;
    }
    const data = await res.json();
    if (!res.ok) { showMsg(data.detail || 'Something went wrong.', true); return; }
    renderPro(data);
    showMsg('', false);
  } catch (e) {
    showMsg('Network error.', true);
  }
});
</script>
</body>
</html>
"""
