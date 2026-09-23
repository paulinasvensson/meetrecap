from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from entitlements import require_pro
from summarizer import summarize_text, extract_action_items

app = FastAPI(title="meetrecap")


class NotesIn(BaseModel):
    text: str


@app.post("/api/summarize/free")
def summarize_free(payload: NotesIn):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please paste some meeting notes.")
    # Free tier: capped, no owner/deadline extraction.
    capped_text = text[:2000]
    summary = summarize_text(capped_text, max_sentences=3)
    actions = extract_action_items(capped_text, max_items=3, with_details=False)
    return {
        "summary": summary,
        "action_items": actions,
        "tier": "free",
        "note": "Free tier: limited to 3 summary lines and 3 action items, no owner/deadline detection.",
    }


@app.post("/api/summarize/pro")
def summarize_pro(payload: NotesIn, _=Depends(require_pro)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please paste some meeting notes.")
    summary = summarize_text(text, max_sentences=8)
    actions = extract_action_items(text, max_items=None, with_details=True)
    return {
        "summary": summary,
        "action_items": actions,
        "tier": "pro",
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>meetrecap — messy notes to clean summaries</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 0 16px; background:#0f172a; color:#e2e8f0; }
  h1 { color:#f8fafc; }
  textarea { width:100%; height:220px; padding:10px; font-size:14px; border-radius:8px; border:1px solid #334155; background:#1e293b; color:#e2e8f0; resize:vertical; }
  button { padding:10px 18px; font-size:14px; border-radius:8px; border:none; cursor:pointer; margin-top:10px; margin-right:8px; }
  .btn-free { background:#334155; color:#e2e8f0; }
  .btn-pro { background:#22c55e; color:#052e16; font-weight:600; }
  .section { margin-top:24px; padding:16px; background:#1e293b; border-radius:10px; border:1px solid #334155; }
  .license-box { margin-top:12px; padding:12px; background:#1e293b; border-radius:8px; border:1px solid #334155;}
  input[type=text] { width:260px; padding:8px; border-radius:6px; border:1px solid #334155; background:#0f172a; color:#e2e8f0; }
  .error { color:#f87171; font-weight:600; }
  .item { padding:8px; margin:6px 0; background:#0f172a; border-left:3px solid #22c55e; border-radius:4px; }
  .meta { font-size:12px; color:#94a3b8; }
  ul { padding-left:20px; }
  code { background:#0f172a; padding:2px 6px; border-radius:4px; }
</style>
</head>
<body>

<h1>📝 meetrecap</h1>
<p>Paste messy meeting notes below. Get a clean summary and action items — instantly.</p>

<textarea id="notes" placeholder="Paste your raw, messy meeting notes here...&#10;e.g. 'ok so we talked about the launch date, John will send the deck by Friday, marketing needs to review the copy asap...'"></textarea>

<div>
  <button class="btn-free" onclick="runFree()">Summarize (Free)</button>
  <button class="btn-pro" onclick="runPro()">Full Recap (Pro)</button>
</div>

<div class="license-box">
  <label>License Key: </label>
  <input type="text" id="licenseKey" placeholder="Paste your license key">
  <button onclick="saveKey()">Save</button>
  <span class="meta">Saved locally in your browser. Sent as X-License-Key on Pro requests.</span>
</div>

<div id="result" class="section" style="display:none;"></div>

<script>
const stored = localStorage.getItem('meetrecap_license_key');
if (stored) document.getElementById('licenseKey').value = stored;

function saveKey() {
  const key = document.getElementById('licenseKey').value.trim();
  localStorage.setItem('meetrecap_license_key', key);
  alert('License key saved.');
}

function renderResult(data, tier) {
  const box = document.getElementById('result');
  box.style.display = 'block';
  let html = `<h3>Summary (${tier})</h3><ul>`;
  (data.summary || []).forEach(s => html += `<li>${escapeHtml(s)}</li>`);
  html += `</ul><h3>Action Items</h3>`;
  if (!data.action_items || data.action_items.length === 0) {
    html += `<p class="meta">No action items detected.</p>`;
  } else {
    data.action_items.forEach(item => {
      html += `<div class="item">${escapeHtml(item.text)}`;
      if (item.owner || item.deadline || item.priority) {
        html += `<div class="meta">`;
        if (item.owner) html += `Owner: <b>${escapeHtml(item.owner)}</b> &nbsp;`;
        if (item.deadline) html += `Deadline: <b>${escapeHtml(item.deadline)}</b> &nbsp;`;
        if (item.priority) html += `Priority: <b>${escapeHtml(item.priority)}</b>`;
        html += `</div>`;
      }
      html += `</div>`;
    });
  }
  if (data.note) html += `<p class="meta">${escapeHtml(data.note)}</p>`;
  box.innerHTML = html;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[m]));
}

async function runFree() {
  const text = document.getElementById('notes').value;
  const box = document.getElementById('result');
  box.style.display = 'block';
  box.innerHTML = 'Working...';
  try {
    const res = await fetch('/api/summarize/free', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await res.json();
    if (!res.ok) { box.innerHTML = `<p class="error">${data.detail || 'Error'}</p>`; return; }
    renderResult(data, 'Free');
  } catch (e) {
    box.innerHTML = `<p class="error">Request failed: ${e}</p>`;
  }
}

async function runPro() {
  const text = document.getElementById('notes').value;
  const key = document.getElementById('licenseKey').value.trim();
  const box = document.getElementById('result');
  box.style.display = 'block';
  box.innerHTML = 'Working...';
  try {
    const res = await fetch('/api/summarize/pro', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-License-Key': key},
      body: JSON.stringify({text})
    });
    const data = await res.json();
    if (res.status === 402) {
      box.innerHTML = `<p class="error">🔒 ${data.detail || 'Payment required.'} Enter a valid license key above and try again.</p>`;
      return;
    }
    if (!res.ok) { box.innerHTML = `<p class="error">${data.detail || 'Error'}</p>`; return; }
    renderResult(data, 'Pro');
  } catch (e) {
    box.innerHTML = `<p class="error">Request failed: ${e}</p>`;
  }
}
</script>

</body>
</html>
"""
