from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from entitlements import require_pro
from recap_engine import free_summarize, full_recap

app = FastAPI(title="meetrecap")


class NotesIn(BaseModel):
    notes: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/api/summarize")
async def summarize(payload: NotesIn):
    if not payload.notes or not payload.notes.strip():
        raise HTTPException(status_code=400, detail="Please paste some meeting notes first.")
    return free_summarize(payload.notes)


@app.post("/api/recap")
async def recap(payload: NotesIn, _license=Depends(require_pro)):
    if not payload.notes or not payload.notes.strip():
        raise HTTPException(status_code=400, detail="Please paste some meeting notes first.")
    return full_recap(payload.notes)


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>meetrecap — messy notes to clean recaps</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 880px; margin: 40px auto; padding: 0 16px; color: #1a1a2e; background: #f7f8fc; }
  h1 { font-size: 1.8rem; margin-bottom: 4px; }
  .sub { color: #555; margin-bottom: 24px; }
  textarea { width: 100%; min-height: 220px; padding: 12px; font-size: 14px; border-radius: 8px; border: 1px solid #ccc; box-sizing: border-box; }
  .row { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
  button { background: #4b3cf5; color: white; border: none; padding: 10px 18px; border-radius: 8px; font-size: 14px; cursor: pointer; }
  button.secondary { background: #eee; color: #333; }
  button:hover { opacity: 0.9; }
  .card { background: white; border-radius: 10px; padding: 18px; margin-top: 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .license-box { display: flex; gap: 8px; align-items: center; margin-bottom: 20px; }
  .license-box input { flex: 1; padding: 8px; border-radius: 6px; border: 1px solid #ccc; }
  .error { color: #b00020; font-weight: 600; }
  .tag { display: inline-block; background: #eef; color: #33c; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 6px; }
  .action-item { border-left: 3px solid #4b3cf5; padding-left: 10px; margin-bottom: 10px; }
  .decision { border-left: 3px solid #22a; padding-left: 10px; margin-bottom: 8px; }
  h3 { margin-bottom: 6px; }
</style>
</head>
<body>

<h1>🗒️ meetrecap</h1>
<div class="sub">Paste your messy meeting notes below. Get a free quick summary instantly, or unlock the full recap with action items, owners, and due dates.</div>

<div class="license-box">
  <label for="licenseKey"><strong>License Key:</strong></label>
  <input id="licenseKey" type="text" placeholder="Paste your license key here" />
  <button class="secondary" onclick="saveKey()">Save</button>
</div>

<textarea id="notes" placeholder="e.g. Discussed Q3 roadmap. Sarah will send the budget doc by Friday. Decided to postpone the launch. @mike needs to update the client tomorrow..."></textarea>

<div class="row">
  <button onclick="doSummarize()">Free Quick Summary</button>
  <button onclick="doRecap()">🔒 Full Recap + Action Items (Pro)</button>
</div>

<div id="results"></div>

<script>
function saveKey() {
  const key = document.getElementById('licenseKey').value.trim();
  localStorage.setItem('meetrecap_license_key', key);
  alert('License key saved.');
}

window.onload = function() {
  const saved = localStorage.getItem('meetrecap_license_key');
  if (saved) document.getElementById('licenseKey').value = saved;
};

function renderError(msg) {
  document.getElementById('results').innerHTML = `<div class="card error">${msg}</div>`;
}

async function doSummarize() {
  const notes = document.getElementById('notes').value;
  const res = await fetch('/api/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes })
  });
  const data = await res.json();
  if (!res.ok) { renderError(data.detail || 'Something went wrong.'); return; }
  document.getElementById('results').innerHTML = `
    <div class="card">
      <span class="tag">FREE</span>
      <h3>Quick Summary</h3>
      <p>${data.summary}</p>
      <p style="color:#888;font-size:13px">${data.note || ''} (${data.line_count} lines analyzed)</p>
    </div>
  `;
}

async function doRecap() {
  const notes = document.getElementById('notes').value;
  const key = localStorage.getItem('meetrecap_license_key') || '';
  const res = await fetch('/api/recap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-License-Key': key },
    body: JSON.stringify({ notes })
  });
  const data = await res.json();

  if (res.status === 402) {
    renderError('🔒 ' + (data.detail || 'This is a paid feature. Enter a valid license key above to unlock it.'));
    return;
  }
  if (!res.ok) { renderError(data.detail || 'Something went wrong.'); return; }

  const actionsHtml = data.action_items.length
    ? data.action_items.map(a => `
        <div class="action-item">
          <strong>${a.task}</strong><br>
          <span style="color:#555;font-size:13px">Owner: ${a.owner} &nbsp;|&nbsp; Due: ${a.due}</span>
        </div>
      `).join('')
    : '<p style="color:#888">No action items detected.</p>';

  const decisionsHtml = data.decisions.length
    ? data.decisions.map(d => `<div class="decision">${d}</div>`).join('')
    : '<p style="color:#888">No decisions detected.</p>';

  document.getElementById('results').innerHTML = `
    <div class="card">
      <span class="tag">PRO</span>
      <h3>Clean Summary</h3>
      <p>${data.clean_summary}</p>
    </div>
    <div class="card">
      <h3>✅ Action Items</h3>
      ${actionsHtml}
    </div>
    <div class="card">
      <h3>📌 Decisions</h3>
      ${decisionsHtml}
    </div>
  `;
}
</script>

</body>
</html>
"""
