# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Index
#
#   GET /   → static "Try it out" mini-site (HTML, no external deps)
#
# Single self-contained page for manual testing of the screenshot and batch
# API surfaces. Served from the same origin so fetch() calls don't need CORS.
# API key is persisted in localStorage so it survives page reloads.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi.responses                                                              import HTMLResponse
from osbot_fast_api.api.decorators.route_path                                      import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                    import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix         import Safe_Str__Fast_API__Route__Prefix


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SG Playwright Service</title>
<style>
:root {
  --bg:#0f1117; --surface:#1a1d27; --surface2:#212437; --border:#2e3149;
  --accent:#4f8ef7; --accent2:#34c88a; --danger:#e05c5c; --warn:#f0a040;
  --text:#d4d8f0; --muted:#6b7094; --radius:8px;
  font-family:'Segoe UI',system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden;}

/* header */
header{background:var(--surface);border-bottom:1px solid var(--border);
       padding:12px 20px;display:flex;align-items:center;gap:14px;flex-shrink:0;}
header h1{font-size:1rem;font-weight:600;flex:1;}
header h1 span{color:var(--accent);}
.badge{font-size:.72rem;padding:3px 10px;border-radius:99px;font-weight:600;border:1px solid var(--border);}
.badge.ok{color:var(--accent2);border-color:var(--accent2);}
.badge.err{color:var(--danger);border-color:var(--danger);}
.badge.chk{color:var(--muted);border-color:var(--muted);}
nav a{color:var(--muted);font-size:.82rem;text-decoration:none;}
nav a:hover{color:var(--accent);}

/* layout */
main{display:grid;grid-template-columns:360px 1fr;flex:1;overflow:hidden;}

/* left panel */
.panel{background:var(--surface);border-right:1px solid var(--border);
       display:flex;flex-direction:column;overflow:hidden;}

/* tabs */
.tabs{display:flex;border-bottom:1px solid var(--border);flex-shrink:0;}
.tab-btn{flex:1;background:transparent;border:none;color:var(--muted);padding:10px;
         font-size:.83rem;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;transition:.15s;}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);}

/* form area */
.tab-pane{display:none;flex-direction:column;gap:12px;padding:16px;overflow-y:auto;flex:1;}
.tab-pane.active{display:flex;}
label{font-size:.75rem;color:var(--muted);display:block;margin-bottom:3px;}
input[type=text],textarea,select{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);
  color:var(--text);padding:7px 10px;font-size:.82rem;font-family:inherit;resize:vertical;}
input[type=text]:focus,textarea:focus{outline:none;border-color:var(--accent);}

/* toggle group */
.tg{display:flex;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border);}
.tg button{flex:1;background:transparent;border:none;color:var(--muted);
           padding:6px;font-size:.78rem;cursor:pointer;transition:.15s;}
.tg button.active{background:var(--accent);color:#fff;}

/* accordion */
details summary{cursor:pointer;font-size:.78rem;color:var(--muted);user-select:none;}
details summary:hover{color:var(--text);}
details>.db{padding-top:8px;display:flex;flex-direction:column;gap:8px;}

/* checkbox */
.ck{display:flex;align-items:center;gap:7px;font-size:.8rem;}
.ck input{width:15px;height:15px;accent-color:var(--accent);cursor:pointer;}

/* api key */
.kr{display:flex;gap:6px;}
.kr input{flex:1;font-family:monospace;font-size:.78rem;}
.ib{background:transparent;border:1px solid var(--border);border-radius:6px;
    color:var(--muted);cursor:pointer;padding:4px 8px;font-size:.78rem;}
.ib:hover{border-color:var(--accent);color:var(--accent);}

/* execute button */
.exec-btn{background:var(--accent);color:#fff;border:none;border-radius:var(--radius);
          padding:10px;font-size:.88rem;font-weight:600;cursor:pointer;flex-shrink:0;}
.exec-btn:hover{opacity:.88;}
.exec-btn:disabled{opacity:.4;cursor:not-allowed;}

/* status */
.sr{display:flex;align-items:center;gap:7px;font-size:.75rem;color:var(--muted);min-height:18px;flex-shrink:0;}
.spin{display:inline-block;width:13px;height:13px;border:2px solid var(--border);
      border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}

/* ── batch items ── */
.batch-toolbar{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.batch-toolbar .tg{flex:1;}
.add-btn{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);
         color:var(--accent);padding:6px 12px;font-size:.8rem;cursor:pointer;white-space:nowrap;}
.add-btn:hover{border-color:var(--accent);}

.url-cards{display:flex;flex-direction:column;gap:8px;overflow-y:auto;flex:1;}

.url-card{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:10px;}
.card-header{display:flex;align-items:center;gap:6px;margin-bottom:6px;}
.card-num{font-size:.7rem;color:var(--muted);background:var(--border);
          border-radius:99px;padding:1px 7px;flex-shrink:0;}
.card-header input{flex:1;background:var(--bg);border:1px solid var(--border);
                   border-radius:6px;color:var(--text);padding:5px 8px;font-size:.8rem;}
.card-header input:focus{outline:none;border-color:var(--accent);}
.rm-btn{background:transparent;border:none;color:var(--muted);cursor:pointer;font-size:1rem;
        padding:2px 4px;flex-shrink:0;}
.rm-btn:hover{color:var(--danger);}
.card-body{display:flex;flex-direction:column;gap:6px;}
.mini-tg{display:flex;border-radius:6px;overflow:hidden;border:1px solid var(--border);}
.mini-tg button{flex:1;background:transparent;border:none;color:var(--muted);
                padding:4px;font-size:.72rem;cursor:pointer;}
.mini-tg button.active{background:var(--accent);color:#fff;}

/* ── right panel ── */
.result{padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;}
.result-meta{font-size:.75rem;color:var(--muted);display:flex;gap:14px;align-items:center;}
.result-meta strong{color:var(--accent2);}
#result-img{max-width:100%;border-radius:var(--radius);border:1px solid var(--border);display:none;}
#result-html{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
             padding:10px;font-size:.73rem;font-family:monospace;white-space:pre-wrap;
             word-break:break-all;display:none;max-height:100%;}
#result-err{color:var(--danger);font-size:.8rem;background:#2a1010;border:1px solid var(--danger);
            border-radius:var(--radius);padding:10px;display:none;}
.placeholder{color:var(--muted);font-size:.88rem;text-align:center;margin:auto;opacity:.5;}

/* batch results grid */
.batch-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;}
.batch-thumb{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}
.batch-thumb img{width:100%;display:block;}
.batch-thumb .thumb-label{padding:6px 8px;font-size:.72rem;color:var(--muted);
                           white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.batch-thumb pre{padding:8px;font-size:.68rem;font-family:monospace;white-space:pre-wrap;
                 word-break:break-all;max-height:160px;overflow:auto;}
</style>
</head>
<body>

<header>
  <h1>SG <span>Playwright</span> Service</h1>
  <span id="health-badge" class="badge chk">checking…</span>
  <nav><a href="/docs" target="_blank">API docs ↗</a></nav>
</header>

<main>
<!-- ────────────── LEFT PANEL ────────────── -->
<div class="panel">

  <!-- API key (always visible) -->
  <div style="padding:12px 16px 0;flex-shrink:0;">
    <label>API Key</label>
    <div class="kr">
      <input id="api-key" type="password" placeholder="paste your API key…">
      <button class="ib" onclick="toggleKeyVis()">👁</button>
    </div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('single')">Single</button>
    <button class="tab-btn"        onclick="switchTab('batch')">Batch</button>
  </div>

  <!-- ── Single tab ── -->
  <div id="tab-single" class="tab-pane active">

    <div>
      <label>URL</label>
      <input id="url" type="text" value="https://sgraph.ai">
    </div>

    <div>
      <label>Format</label>
      <div class="tg">
        <button id="fmt-png"  class="active" onclick="setFmt('png')">PNG screenshot</button>
        <button id="fmt-html" class=""       onclick="setFmt('html')">HTML source</button>
      </div>
    </div>

    <details>
      <summary>▸ Advanced options</summary>
      <div class="db">
        <div>
          <label>JavaScript expression (runs before capture)</label>
          <textarea id="js-expr" rows="2" placeholder="e.g. document.body.style.zoom='80%'"></textarea>
        </div>
        <div>
          <label>Click selector (before capture)</label>
          <input id="click-sel" type="text" placeholder="e.g. button#accept-cookies">
        </div>
        <div class="ck">
          <input id="full-page" type="checkbox">
          <label for="full-page">Full-page screenshot</label>
        </div>
      </div>
    </details>

    <button class="exec-btn" id="btn-single" onclick="execSingle()">Execute</button>
    <div class="sr">
      <span id="spin-s" style="display:none" class="spin"></span>
      <span id="status-s"></span>
    </div>

  </div>

  <!-- ── Batch tab ── -->
  <div id="tab-batch" class="tab-pane">

    <!-- mode + add button -->
    <div class="batch-toolbar">
      <div class="tg" style="flex:1">
        <button id="bm-items" class="active" onclick="setBatchMode('items')">Independent sessions</button>
        <button id="bm-steps" class=""       onclick="setBatchMode('steps')">Sequential steps</button>
      </div>
    </div>

    <!-- screenshot_per_step (steps mode only) -->
    <div id="sps-row" class="ck" style="display:none">
      <input id="sps-chk" type="checkbox" checked>
      <label for="sps-chk">Screenshot after each step</label>
    </div>

    <!-- URL cards list -->
    <div class="url-cards" id="url-cards"></div>

    <button class="add-btn" onclick="addCard()">+ Add URL</button>

    <button class="exec-btn" id="btn-batch" onclick="execBatch()">Execute Batch</button>
    <div class="sr">
      <span id="spin-b" style="display:none" class="spin"></span>
      <span id="status-b"></span>
    </div>

  </div>
</div>

<!-- ────────────── RIGHT PANEL ────────────── -->
<div class="result" id="result-panel">
  <div class="result-meta" id="result-meta" style="display:none">
    <strong id="meta-fmt"></strong>
    <span id="meta-dur"></span>ms
    <span id="meta-trace" style="font-family:monospace;font-size:.7rem"></span>
  </div>
  <img  id="result-img"  alt="screenshot">
  <pre  id="result-html"></pre>
  <pre  id="result-err"></pre>
  <div  id="batch-grid"  class="batch-grid"></div>
  <p class="placeholder" id="placeholder">Enter a URL and click Execute</p>
</div>
</main>

<script>
const KEY_LS = 'sg_playwright_api_key';
const keyEl  = document.getElementById('api-key');
keyEl.value  = localStorage.getItem(KEY_LS) || '';
keyEl.addEventListener('input', () => localStorage.setItem(KEY_LS, keyEl.value));

function toggleKeyVis() { keyEl.type = keyEl.type === 'password' ? 'text' : 'password'; }

// ── Tabs ──
function switchTab(t) {
  ['single','batch'].forEach(n => {
    document.getElementById('tab-'+n).classList.toggle('active', n===t);
    document.querySelectorAll('.tab-btn')[n==='single'?0:1].classList.toggle('active', n===t);
  });
  clearResult();
}

// ── Single ──
let fmt = 'png';
function setFmt(f) {
  fmt = f;
  document.getElementById('fmt-png') .classList.toggle('active', f==='png');
  document.getElementById('fmt-html').classList.toggle('active', f==='html');
}

async function execSingle() {
  const url    = document.getElementById('url').value.trim();
  const apiKey = keyEl.value.trim();
  const js     = document.getElementById('js-expr').value.trim();
  const click  = document.getElementById('click-sel').value.trim();
  const full   = document.getElementById('full-page').checked;
  if (!url)    { setStatus('s','⚠ URL required',true); return; }
  if (!apiKey) { setStatus('s','⚠ API key required',true); return; }
  const body = {url, format:fmt};
  if (js)    body.javascript = js;
  if (click) body.click      = click;
  if (full)  body.full_page  = true;
  setBusy('s', true);
  clearResult();
  try {
    const r    = await post('/screenshot', apiKey, body);
    const data = await r.json();
    if (!r.ok) { showErr(JSON.stringify(data,null,2)); return; }
    showMeta(fmt, data.duration_ms, data.trace_id);
    if (fmt==='png' && data.screenshot_b64) {
      const img = document.getElementById('result-img');
      img.src = 'data:image/png;base64,'+data.screenshot_b64;
      img.style.display = 'block';
    } else if (fmt==='html' && data.html) {
      const pre = document.getElementById('result-html');
      pre.textContent = data.html; pre.style.display='block';
    }
    setStatus('s', `Done in ${data.duration_ms}ms`);
  } catch(e) { showErr('Network error: '+e.message); }
  finally    { setBusy('s', false); }
}

// ── Batch mode ──
let batchMode = 'items';
function setBatchMode(m) {
  batchMode = m;
  document.getElementById('bm-items').classList.toggle('active', m==='items');
  document.getElementById('bm-steps').classList.toggle('active', m==='steps');
  document.getElementById('sps-row').style.display = m==='steps' ? 'flex' : 'none';
  // re-label cards
  document.querySelectorAll('.card-num').forEach((el,i) =>
    el.textContent = m==='steps' ? `step ${i+1}` : `#${i+1}`);
}

// ── URL cards ──
let cardId = 0;
function addCard(url='') {
  const id  = ++cardId;
  const idx = document.querySelectorAll('.url-card').length + 1;
  const label = batchMode==='steps' ? `step ${idx}` : `#${idx}`;
  const div = document.createElement('div');
  div.className = 'url-card'; div.dataset.id = id;
  div.innerHTML = `
    <div class="card-header">
      <span class="card-num">${label}</span>
      <input type="text" value="${url}" placeholder="https://…" oninput="cardField(${id},'url',this.value)">
      <button class="rm-btn" onclick="removeCard(${id})" title="Remove">×</button>
    </div>
    <div class="card-body">
      <div class="mini-tg">
        <button class="active" onclick="cardFmt(${id},'png',this)">PNG</button>
        <button class=""       onclick="cardFmt(${id},'html',this)">HTML</button>
      </div>
      <details>
        <summary style="font-size:.74rem;color:var(--muted)">▸ options</summary>
        <div class="db" style="padding-top:6px">
          <input type="text" placeholder="JS expression…" oninput="cardField(${id},'javascript',this.value)">
          <input type="text" placeholder="click selector…" oninput="cardField(${id},'click',this.value)">
          <label class="ck" style="margin-top:2px">
            <input type="checkbox" onchange="cardField(${id},'full_page',this.checked)">
            <span>Full-page</span>
          </label>
        </div>
      </details>
    </div>`;
  document.getElementById('url-cards').appendChild(div);
  cardData[id] = {url, format:'png'};
  reNumberCards();
}

const cardData = {};
function cardField(id, key, val) {
  if (!cardData[id]) cardData[id]={format:'png'};
  if (val==='' || val===false) delete cardData[id][key];
  else cardData[id][key] = val;
}
function cardFmt(id, f, btn) {
  btn.parentElement.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  cardData[id].format = f;
}
function removeCard(id) {
  const el = document.querySelector(`.url-card[data-id="${id}"]`);
  if (el) el.remove();
  delete cardData[id];
  reNumberCards();
}
function reNumberCards() {
  document.querySelectorAll('.url-card').forEach((el, i) => {
    const num = el.querySelector('.card-num');
    num.textContent = batchMode==='steps' ? `step ${i+1}` : `#${i+1}`;
  });
}

function getCardItems() {
  return [...document.querySelectorAll('.url-card')].map(el => {
    const id  = el.dataset.id;
    const url = el.querySelector('input[type=text]').value.trim();
    const d   = {...(cardData[id]||{}), url};
    // clean nulls
    const out = {url: d.url, format: d.format||'png'};
    if (d.javascript) out.javascript = d.javascript;
    if (d.click)      out.click      = d.click;
    if (d.full_page)  out.full_page  = true;
    return out;
  }).filter(x => x.url);
}

async function execBatch() {
  const apiKey = keyEl.value.trim();
  if (!apiKey) { setStatus('b','⚠ API key required',true); return; }
  const items = getCardItems();
  if (!items.length) { setStatus('b','⚠ Add at least one URL',true); return; }
  const sps = document.getElementById('sps-chk').checked;
  const body = batchMode==='items'
    ? {items}
    : {steps: items, screenshot_per_step: sps};
  setBusy('b', true);
  clearResult();
  try {
    const r    = await post('/screenshot/batch', apiKey, body);
    const data = await r.json();
    if (!r.ok) { showErr(JSON.stringify(data,null,2)); return; }
    const shots = data.screenshots || [];
    showBatchGrid(shots, items, data.duration_ms);
    setStatus('b', `${shots.length} screenshot${shots.length!==1?'s':''} in ${data.duration_ms}ms`);
  } catch(e) { showErr('Network error: '+e.message); }
  finally    { setBusy('b', false); }
}

function showBatchGrid(shots, items, totalMs) {
  document.getElementById('placeholder').style.display = 'none';
  document.getElementById('result-meta').style.display = 'flex';
  document.getElementById('meta-fmt').textContent = `${shots.length} result${shots.length!==1?'s':''}`;
  document.getElementById('meta-dur').textContent = totalMs ?? '?';
  document.getElementById('meta-trace').textContent = '';
  const grid = document.getElementById('batch-grid');
  grid.innerHTML = '';
  shots.forEach((s, i) => {
    const url   = (items[i]||{}).url || `#${i+1}`;
    const thumb = document.createElement('div');
    thumb.className = 'batch-thumb';
    if (s.screenshot_b64) {
      thumb.innerHTML = `<img src="data:image/png;base64,${s.screenshot_b64}" loading="lazy">
        <div class="thumb-label" title="${url}">${i+1}. ${url}</div>`;
    } else if (s.html) {
      thumb.innerHTML = `<pre>${escHtml(s.html.slice(0,400))}…</pre>
        <div class="thumb-label" title="${url}">${i+1}. ${url} (HTML)</div>`;
    } else {
      thumb.innerHTML = `<div class="thumb-label" style="color:var(--warn)">No result for ${url}</div>`;
    }
    grid.appendChild(thumb);
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Shared helpers ──
function post(path, key, body) {
  return fetch(path, {method:'POST',
    headers:{'Content-Type':'application/json','X-API-Key':key},
    body:JSON.stringify(body)});
}

function setBusy(which, on) {
  const btn  = document.getElementById('btn-'+(which==='s'?'single':'batch'));
  const spin = document.getElementById('spin-'+which);
  btn.disabled = on;
  spin.style.display = on ? 'inline-block' : 'none';
  if (on) setStatus(which, 'Running…');
}

function setStatus(which, msg, warn) {
  const el = document.getElementById('status-'+which);
  el.textContent = msg;
  el.style.color = warn ? 'var(--danger)' : 'var(--muted)';
}

function clearResult() {
  ['result-img','result-html','result-err','result-meta'].forEach(id =>
    document.getElementById(id).style.display='none');
  document.getElementById('batch-grid').innerHTML = '';
  document.getElementById('placeholder').style.display='block';
}

function showErr(msg) {
  const el = document.getElementById('result-err');
  el.textContent = msg; el.style.display='block';
  document.getElementById('placeholder').style.display='none';
}

function showMeta(f, dur, trace) {
  document.getElementById('meta-fmt').textContent   = f.toUpperCase();
  document.getElementById('meta-dur').textContent   = dur??'?';
  document.getElementById('meta-trace').textContent = trace??'';
  document.getElementById('result-meta').style.display='flex';
  document.getElementById('placeholder').style.display='none';
}

// ── Health check ──
async function checkHealth() {
  const badge = document.getElementById('health-badge');
  try {
    const r = await fetch('/health/status');
    const d = await r.json();
    const ok = d.healthy===true;
    badge.textContent = ok ? '● healthy' : '● degraded';
    badge.className   = 'badge '+(ok?'ok':'err');
  } catch { badge.textContent='● unreachable'; badge.className='badge err'; }
}
checkHealth();

// ── Seed batch with two blank cards ──
addCard('https://sgraph.ai');
addCard('');

// Ctrl/Cmd+Enter executes the active tab
document.addEventListener('keydown', e => {
  if (!(e.ctrlKey||e.metaKey) || e.key!=='Enter') return;
  const active = document.querySelector('.tab-pane.active').id;
  if (active==='tab-single') execSingle();
  else                       execBatch();
});
</script>
</body>
</html>
"""


class Routes__Index(Fast_API__Routes):
    tag : str = 'index'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')    # Mount at root

    @route_path('/')
    def index(self) -> HTMLResponse:
        return HTMLResponse(content=INDEX_HTML)

    def setup_routes(self):
        self.add_route_get(self.index)
