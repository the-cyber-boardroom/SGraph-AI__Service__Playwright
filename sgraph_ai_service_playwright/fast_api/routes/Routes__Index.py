# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Index
#
#   GET /   → static "Try it out" mini-site (HTML, no external deps)
#
# Single self-contained page for manual testing of the screenshot API surface.
# Served from the same origin so fetch() calls don't need CORS. API key is
# persisted in localStorage so it survives page reloads.
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
    --bg:       #0f1117;
    --surface:  #1a1d27;
    --border:   #2e3149;
    --accent:   #4f8ef7;
    --accent2:  #34c88a;
    --danger:   #e05c5c;
    --text:     #d4d8f0;
    --muted:    #6b7094;
    --radius:   8px;
    font-family: 'Segoe UI', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }

  /* ── Header ── */
  header { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 14px 24px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 1.1rem; font-weight: 600; flex: 1; }
  header h1 span { color: var(--accent); }
  .badge { font-size: .75rem; padding: 3px 10px; border-radius: 99px; font-weight: 600;
           border: 1px solid var(--border); }
  .badge.ok  { color: var(--accent2); border-color: var(--accent2); }
  .badge.err { color: var(--danger);  border-color: var(--danger);  }
  .badge.chk { color: var(--muted);   border-color: var(--muted);   }
  nav a { color: var(--muted); font-size: .85rem; text-decoration: none; }
  nav a:hover { color: var(--accent); }

  /* ── Layout ── */
  main { display: grid; grid-template-columns: 380px 1fr; gap: 0; flex: 1; }

  /* ── Left panel (controls) ── */
  .panel { background: var(--surface); border-right: 1px solid var(--border);
           padding: 20px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
  label { font-size: .78rem; color: var(--muted); display: block; margin-bottom: 4px; }
  input[type=text], textarea, select {
    width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius);
    color: var(--text); padding: 8px 10px; font-size: .85rem; font-family: inherit; resize: vertical; }
  input[type=text]:focus, textarea:focus { outline: none; border-color: var(--accent); }

  .row { display: flex; gap: 8px; align-items: center; }
  .row label { margin: 0; }

  /* format toggle */
  .toggle-group { display: flex; border-radius: var(--radius); overflow: hidden;
                  border: 1px solid var(--border); }
  .toggle-group button { flex: 1; background: transparent; border: none; color: var(--muted);
                         padding: 7px; font-size: .82rem; cursor: pointer; transition: background .15s; }
  .toggle-group button.active { background: var(--accent); color: #fff; }

  /* accordion */
  details summary { cursor: pointer; font-size: .8rem; color: var(--muted); user-select: none; padding: 4px 0; }
  details summary:hover { color: var(--text); }
  details > .detail-body { padding-top: 10px; display: flex; flex-direction: column; gap: 10px; }

  /* checkboxes */
  .check-row { display: flex; align-items: center; gap: 8px; font-size: .83rem; }
  .check-row input { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }

  /* API key */
  .key-row { display: flex; gap: 6px; }
  .key-row input { flex: 1; font-family: monospace; font-size: .8rem; }
  .icon-btn { background: transparent; border: 1px solid var(--border); border-radius: 6px;
              color: var(--muted); cursor: pointer; padding: 4px 8px; font-size: .8rem; }
  .icon-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* execute button */
  #btn-exec { background: var(--accent); color: #fff; border: none; border-radius: var(--radius);
              padding: 11px; font-size: .9rem; font-weight: 600; cursor: pointer; transition: opacity .15s; }
  #btn-exec:hover { opacity: .88; }
  #btn-exec:disabled { opacity: .4; cursor: not-allowed; }

  /* status row */
  .status-row { display: flex; align-items: center; gap: 8px; font-size: .78rem; color: var(--muted); min-height: 20px; }
  .spin { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border);
          border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Right panel (result) ── */
  .result { padding: 20px; overflow: auto; display: flex; flex-direction: column; gap: 12px; }
  .result-header { font-size: .78rem; color: var(--muted); display: flex; gap: 16px; align-items: center; }
  .result-header strong { color: var(--accent2); }
  #result-img { max-width: 100%; border-radius: var(--radius); border: 1px solid var(--border); display: none; }
  #result-html { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
                 padding: 12px; font-size: .78rem; font-family: monospace; white-space: pre-wrap;
                 word-break: break-all; max-height: calc(100vh - 120px); overflow: auto; display: none; }
  #result-err  { color: var(--danger); font-size: .83rem; background: #2a1010; border: 1px solid var(--danger);
                 border-radius: var(--radius); padding: 12px; display: none; }
  .placeholder { color: var(--muted); font-size: .9rem; text-align: center; margin: auto; opacity: .5; }

  @media (max-width: 720px) {
    main { grid-template-columns: 1fr; }
    .panel { border-right: none; border-bottom: 1px solid var(--border); }
  }
</style>
</head>
<body>

<header>
  <h1>SG <span>Playwright</span> Service</h1>
  <span id="health-badge" class="badge chk">checking…</span>
  <nav><a href="/docs" target="_blank">API docs ↗</a></nav>
</header>

<main>
  <!-- ── Controls ── -->
  <div class="panel">

    <!-- API key -->
    <div>
      <label>API Key</label>
      <div class="key-row">
        <input id="api-key" type="password" placeholder="paste your API key…">
        <button class="icon-btn" onclick="toggleKeyVis()">👁</button>
      </div>
    </div>

    <!-- URL -->
    <div>
      <label>URL</label>
      <input id="url" type="text" value="https://sgraph.ai">
    </div>

    <!-- Format -->
    <div>
      <label>Format</label>
      <div class="toggle-group">
        <button id="fmt-png"  class="active" onclick="setFmt('png')">PNG screenshot</button>
        <button id="fmt-html" class=""       onclick="setFmt('html')">HTML source</button>
      </div>
    </div>

    <!-- Advanced -->
    <details>
      <summary>▸ Advanced options</summary>
      <div class="detail-body">
        <div>
          <label>JavaScript expression (runs before capture)</label>
          <textarea id="js-expr" rows="2" placeholder="e.g. document.body.style.zoom='80%'"></textarea>
        </div>
        <div>
          <label>Click selector (before capture)</label>
          <input id="click-sel" type="text" placeholder="e.g. button#accept-cookies">
        </div>
        <div class="check-row">
          <input id="full-page" type="checkbox">
          <label for="full-page">Full-page screenshot</label>
        </div>
      </div>
    </details>

    <button id="btn-exec" onclick="execute()">Execute</button>

    <div class="status-row">
      <span id="status-spin" style="display:none" class="spin"></span>
      <span id="status-text"></span>
    </div>

  </div>

  <!-- ── Result ── -->
  <div class="result">
    <div class="result-header" id="result-meta" style="display:none">
      Result: <strong id="meta-fmt"></strong> &nbsp;·&nbsp;
      <span id="meta-dur"></span>ms &nbsp;·&nbsp;
      <span id="meta-trace" style="font-family:monospace;font-size:.72rem"></span>
    </div>
    <img  id="result-img"  alt="screenshot">
    <pre  id="result-html"></pre>
    <pre  id="result-err"></pre>
    <p class="placeholder" id="placeholder">Enter a URL and click Execute</p>
  </div>
</main>

<script>
  const KEY_LS = 'sg_playwright_api_key';

  // ── Restore API key from localStorage ──
  const keyEl = document.getElementById('api-key');
  keyEl.value = localStorage.getItem(KEY_LS) || '';
  keyEl.addEventListener('input', () => localStorage.setItem(KEY_LS, keyEl.value));

  function toggleKeyVis() {
    keyEl.type = keyEl.type === 'password' ? 'text' : 'password';
  }

  // ── Format toggle ──
  let fmt = 'png';
  function setFmt(f) {
    fmt = f;
    document.getElementById('fmt-png') .classList.toggle('active', f === 'png');
    document.getElementById('fmt-html').classList.toggle('active', f === 'html');
  }

  // ── Health check ──
  async function checkHealth() {
    const badge = document.getElementById('health-badge');
    try {
      const r = await fetch('/health/status');
      const d = await r.json();
      const ok = d.healthy === true;
      badge.textContent = ok ? '● healthy' : '● degraded';
      badge.className = 'badge ' + (ok ? 'ok' : 'err');
    } catch(e) {
      badge.textContent = '● unreachable';
      badge.className = 'badge err';
    }
  }
  checkHealth();

  // ── Execute ──
  async function execute() {
    const url     = document.getElementById('url').value.trim();
    const apiKey  = document.getElementById('api-key').value.trim();
    const jsExpr  = document.getElementById('js-expr').value.trim();
    const clickSel= document.getElementById('click-sel').value.trim();
    const fullPage= document.getElementById('full-page').checked;

    if (!url)    { setStatus('⚠ URL is required', true); return; }
    if (!apiKey) { setStatus('⚠ API key is required', true); return; }

    const body = { url, format: fmt };
    if (jsExpr)   body.javascript = jsExpr;
    if (clickSel) body.click      = clickSel;
    if (fullPage) body.full_page  = true;

    setBusy(true);
    clearResult();

    try {
      const r = await fetch('/screenshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify(body)
      });

      const data = await r.json();

      if (!r.ok) {
        showError(`HTTP ${r.status}\n${JSON.stringify(data, null, 2)}`);
        return;
      }

      showMeta(fmt, data.duration_ms, data.trace_id);

      if (fmt === 'png' && data.screenshot_b64) {
        const img = document.getElementById('result-img');
        img.src = 'data:image/png;base64,' + data.screenshot_b64;
        img.style.display = 'block';
      } else if (fmt === 'html' && data.html) {
        const pre = document.getElementById('result-html');
        pre.textContent = data.html;
        pre.style.display = 'block';
      } else {
        showError('Unexpected response:\n' + JSON.stringify(data, null, 2));
      }
    } catch(e) {
      showError('Network error: ' + e.message);
    } finally {
      setBusy(false);
    }
  }

  function setBusy(on) {
    document.getElementById('btn-exec').disabled = on;
    document.getElementById('status-spin').style.display = on ? 'inline-block' : 'none';
    if (on) document.getElementById('status-text').textContent = 'Running…';
    else    document.getElementById('status-text').textContent = '';
  }

  function setStatus(msg, warn) {
    document.getElementById('status-text').textContent = msg;
    document.getElementById('status-text').style.color = warn ? 'var(--danger)' : 'var(--muted)';
  }

  function clearResult() {
    document.getElementById('result-img') .style.display = 'none';
    document.getElementById('result-html').style.display = 'none';
    document.getElementById('result-err') .style.display = 'none';
    document.getElementById('result-meta').style.display = 'none';
    document.getElementById('placeholder').style.display = 'block';
  }

  function showError(msg) {
    const el = document.getElementById('result-err');
    el.textContent = msg;
    el.style.display = 'block';
    document.getElementById('placeholder').style.display = 'none';
    setStatus('Failed', true);
  }

  function showMeta(fmt, dur, trace) {
    document.getElementById('meta-fmt').textContent   = fmt.toUpperCase();
    document.getElementById('meta-dur').textContent   = dur ?? '?';
    document.getElementById('meta-trace').textContent = trace ?? '';
    document.getElementById('result-meta').style.display = 'flex';
    document.getElementById('placeholder').style.display = 'none';
    setStatus(`Done in ${dur}ms`);
  }

  // Allow Ctrl+Enter / Cmd+Enter to execute
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') execute();
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
