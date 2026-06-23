# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Index
#
#   GET /   → static capability-driven "Try it out" console (HTML, served same-origin)
#
# Rebuilt for the v0.2.64 dev pack (P2-P5): a capability-driven, agent-native console
# that exposes the full service surface — the 24-verb /sequence language, /inspect,
# /session/*, /browser/* one-shots, a Debug panel, and the live /health/capabilities
# self-description — plus portable workflow import/export, in-app docs, and an agentic
# window.__tool JS API.
#
# Loading model (Decision #1 / #11, brief 08):
#   - sg-tokens + sg-layout are loaded CDN-absolute from https://dev.tools.sgraph.ai/...
#     (prefix-independent — works identically behind /pw and at root), mirroring the
#     admin dashboard (sgraph_ai_service_playwright__api_site/admin/index.html:7,19;
#     admin.js:194-195). The console degrades gracefully if the CDN is unreachable —
#     its own tab shell renders without sg-layout so the page is self-sufficient offline.
#   - Every SAME-ORIGIN fetch / asset stays window.API_BASE-prefixed (forbidden:
#     absolute-rooted /components-style URLs — they break behind the /pw proxy).
#
# sg-tool-api note: the shared sg-tool-api web component (which the pack assumes
# registers window.__tool) was NOT reachable on the CDN as of this build — both
# https://dev.tools.sgraph.ai/core/sg-tool-api/v0.1.0/sg-tool-api.js and the
# /components/core/... convention returned 404 (sg-layout at the analogous path IS
# reachable). So window.__tool is registered HERE as an in-page, contract-compatible
# local registration of the documented sg-tool-api surface (window.__tool + meta.* +
# SGA_TOOL + __tool_registry). It is byte-compatible with the house pattern, so an
# agent that knows sg-tool-api needs no sg-playwright-specific knowledge.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                        import Request
from fastapi.responses                                                              import HTMLResponse
from osbot_fast_api.api.decorators.route_path                                      import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                    import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix         import Safe_Str__Fast_API__Route__Prefix

from sg_compute_specs.playwright.core.service.Root_Path__Resolver                  import Root_Path__Resolver


INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SG Playwright Service — Console</title>
<script>window.API_BASE="__API_BASE__";</script>
<!-- sg-tokens (design tokens): CDN-absolute → prefix-independent, works behind /pw and at root (Decision #11, brief 08; mirrors admin index.html:7). Layout is an in-house resizable grid (no sg-layout dependency). -->
<link rel="stylesheet" href="https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css">
<style>
:root {
  --bg:#0f1117; --surface:#1a1d27; --surface2:#212437; --border:#2e3149;
  --accent:#4f8ef7; --accent2:#34c88a; --danger:#e05c5c; --warn:#f0a040;
  --text:#d4d8f0; --muted:#6b7094; --radius:8px;
  /* Light work-pane palette (Decision #1): builder + result + console panes use
     a light surface with dark text. Header + tab rail keep the dark tokens. */
  --lbg:#ffffff; --lsurface:#f5f6fa; --lsurface2:#eceef4; --lborder:#d3d7e2;
  --ltext:#1c2233; --lmuted:#5a6379;
  font-family:'Segoe UI',system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden;}

header{background:var(--surface);border-bottom:1px solid var(--border);
       padding:10px 18px;display:flex;align-items:center;gap:14px;flex-shrink:0;flex-wrap:wrap;}
header h1{font-size:1rem;font-weight:600;}
header h1 span{color:var(--accent);}
.badge{font-size:.72rem;padding:3px 10px;border-radius:99px;font-weight:600;border:1px solid var(--border);}
.badge.ok{color:var(--accent2);border-color:var(--accent2);}
.badge.err{color:var(--danger);border-color:var(--danger);}
.badge.chk{color:var(--muted);border-color:var(--muted);}
nav{margin-left:auto;display:flex;gap:14px;align-items:center;}
nav a{color:var(--muted);font-size:.82rem;text-decoration:none;cursor:pointer;}
nav a:hover{color:var(--accent);}

/* auth bar */
.authbar{background:var(--surface);border-bottom:1px solid var(--border);
         padding:8px 18px;display:flex;align-items:center;gap:12px;flex-shrink:0;flex-wrap:wrap;}
.authbar label{font-size:.72rem;color:var(--muted);}
.tg{display:flex;border-radius:6px;overflow:hidden;border:1px solid var(--border);}
.tg button{background:transparent;border:none;color:var(--muted);padding:5px 10px;
           font-size:.74rem;cursor:pointer;transition:.15s;white-space:nowrap;}
.tg button.active{background:var(--accent);color:#fff;}
.kr{display:flex;gap:6px;align-items:center;flex:1;min-width:200px;}
.kr input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;
          color:var(--text);padding:5px 8px;font-family:monospace;font-size:.78rem;}
.ib{background:transparent;border:1px solid var(--border);border-radius:6px;
    color:var(--muted);cursor:pointer;padding:4px 8px;font-size:.78rem;}
.ib:hover{border-color:var(--accent);color:var(--accent);}
.keynote{font-size:.66rem;color:var(--muted);opacity:.8;}

main{display:grid;grid-template-columns:170px 1fr;flex:1;overflow:hidden;}

/* tab rail */
.tab-rail{background:var(--surface);border-right:1px solid var(--border);
          display:flex;flex-direction:column;overflow-y:auto;flex-shrink:0;}
.tab-rail button{background:transparent;border:none;border-left:3px solid transparent;
                 color:var(--muted);padding:11px 14px;font-size:.84rem;font-weight:600;
                 cursor:pointer;text-align:left;transition:.15s;}
.tab-rail button.active{color:var(--accent);border-left-color:var(--accent);background:var(--surface2);}
.tab-rail button:disabled{opacity:.35;cursor:not-allowed;}
.tab-rail button .cap-off{font-size:.62rem;color:var(--warn);display:block;font-weight:400;}

/* split: builder | result */
.split{display:grid;grid-template-columns:minmax(360px,1fr) minmax(360px,1fr);overflow:hidden;}
.builder{background:var(--surface);border-right:1px solid var(--border);
         padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;}
.result{padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;}

.tab-pane{display:none;flex-direction:column;gap:12px;}
.tab-pane.active{display:flex;}

label{font-size:.74rem;color:var(--muted);display:block;margin-bottom:3px;}
input[type=text],input[type=number],textarea,select{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);
  color:var(--text);padding:7px 10px;font-size:.82rem;font-family:inherit;resize:vertical;}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent);}
textarea{font-family:monospace;}

details summary{cursor:pointer;font-size:.78rem;color:var(--muted);user-select:none;}
details summary:hover{color:var(--text);}
details>.db{padding-top:8px;display:flex;flex-direction:column;gap:8px;}
.ck{display:flex;align-items:center;gap:7px;font-size:.8rem;}
.ck input{width:15px;height:15px;accent-color:var(--accent);cursor:pointer;}

.btn-row{display:flex;gap:8px;flex-wrap:wrap;flex-shrink:0;}
.exec-btn{background:var(--accent);color:#fff;border:none;border-radius:var(--radius);
          padding:9px 16px;font-size:.86rem;font-weight:600;cursor:pointer;}
.exec-btn:hover{opacity:.88;}
.exec-btn:disabled{opacity:.4;cursor:not-allowed;}
.gbtn{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);
      color:var(--text);padding:8px 12px;font-size:.78rem;cursor:pointer;}
.gbtn:hover{border-color:var(--accent);color:var(--accent);}
.add-btn{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);
         color:var(--accent);padding:6px 12px;font-size:.8rem;cursor:pointer;}
.add-btn:hover{border-color:var(--accent);}

.sr{display:flex;align-items:center;gap:7px;font-size:.75rem;color:var(--muted);min-height:18px;}
.spin{display:inline-block;width:13px;height:13px;border:2px solid var(--border);
      border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}

.hint{font-size:.7rem;color:var(--warn);background:#2a2210;border:1px solid var(--warn);
      border-radius:6px;padding:6px 8px;}
.section-title{font-size:.82rem;font-weight:600;color:var(--text);}

/* step cards */
.step-card{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:10px;}
.step-head{display:flex;align-items:center;gap:6px;margin-bottom:6px;}
.step-head .num{font-size:.7rem;color:var(--muted);background:var(--border);border-radius:99px;padding:1px 7px;}
.step-head select{flex:1;}
.rm-btn{background:transparent;border:none;color:var(--muted);cursor:pointer;font-size:1rem;padding:2px 4px;}
.rm-btn:hover{color:var(--danger);}
.mv-btn{background:transparent;border:1px solid var(--border);border-radius:5px;color:var(--muted);
        cursor:pointer;font-size:.7rem;padding:2px 5px;}
.mv-btn:hover{color:var(--accent);border-color:var(--accent);}
.step-fields{display:flex;flex-direction:column;gap:6px;}
.step-fields .fr{display:flex;flex-direction:column;gap:2px;}

/* result viewer */
.result-meta{font-size:.75rem;color:var(--muted);display:flex;gap:14px;align-items:center;flex-wrap:wrap;}
.result-meta strong{color:var(--accent2);}
.pill{font-size:.68rem;padding:2px 8px;border-radius:99px;border:1px solid var(--border);}
.pill.passed{color:var(--accent2);border-color:var(--accent2);}
.pill.failed{color:var(--danger);border-color:var(--danger);}
.pill.skipped{color:var(--muted);}
.pill.partial{color:var(--warn);border-color:var(--warn);}
#result-img{max-width:100%;border-radius:var(--radius);border:1px solid var(--border);display:none;}
pre.out{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
        padding:10px;font-size:.72rem;font-family:monospace;white-space:pre-wrap;word-break:break-all;
        max-height:420px;overflow:auto;}
#result-err{color:var(--danger);font-size:.8rem;background:#2a1010;border:1px solid var(--danger);
            border-radius:var(--radius);padding:10px;display:none;white-space:pre-wrap;}
.placeholder{color:var(--muted);font-size:.88rem;text-align:center;margin:auto;opacity:.5;}
.step-result{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:8px 10px;}
.step-result .srh{display:flex;align-items:center;gap:8px;font-size:.76rem;}
.step-result img{max-width:100%;margin-top:6px;border:1px solid var(--border);border-radius:6px;}
.batch-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;}
.batch-thumb{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}
.batch-thumb img{width:100%;display:block;}
.batch-thumb .thumb-label{padding:6px 8px;font-size:.7rem;color:var(--muted);
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

/* gallery */
.gallery{display:flex;flex-direction:column;gap:6px;}
.gallery button{text-align:left;background:var(--surface2);border:1px solid var(--border);
                border-radius:6px;color:var(--text);padding:8px 10px;cursor:pointer;font-size:.78rem;}
.gallery button:hover{border-color:var(--accent);}
.gallery .gw{color:var(--accent);font-weight:600;}
.gallery .gd{color:var(--muted);font-size:.68rem;display:block;margin-top:2px;}

/* docs */
.docs-verb{border:1px solid var(--border);border-radius:6px;margin-bottom:6px;background:var(--surface2);}
.docs-verb summary{padding:7px 10px;font-size:.78rem;font-weight:600;color:var(--accent);}
.docs-verb .dv-body{padding:0 10px 8px;font-size:.72rem;color:var(--muted);}
.cap-table{width:100%;border-collapse:collapse;font-size:.74rem;}
.cap-table td{border:1px solid var(--border);padding:5px 8px;}
.cap-table td:first-child{color:var(--muted);width:45%;}

/* ══ Light work panes (Decision #1) — builder (center) + result (right) + console
      (bottom) read on white. Header + .tab-rail keep the dark tokens above. The
      `.work-light` class is applied to those three panes only; everything below is
      scoped under it so the dark chrome is never touched. ══ */
.work-light{background:var(--lsurface);color:var(--ltext);}
.work-light .section-title{color:var(--ltext);}
.work-light label{color:var(--lmuted);}
.work-light input[type=text],.work-light input[type=number],.work-light input[type=password],
.work-light textarea,.work-light select{
  background:var(--lbg);border:1px solid var(--lborder);color:var(--ltext);}
.work-light input:focus,.work-light textarea:focus,.work-light select:focus{border-color:var(--accent);}
.work-light .gbtn,.work-light .add-btn,.work-light .ib{
  background:var(--lsurface2);border:1px solid var(--lborder);color:var(--ltext);}
.work-light .gbtn:hover,.work-light .add-btn:hover,.work-light .ib:hover{border-color:var(--accent);color:var(--accent);}
.work-light .step-card,.work-light .gallery button{background:var(--lbg);border:1px solid var(--lborder);color:var(--ltext);}
.work-light .gallery button:hover{border-color:var(--accent);}
.work-light .step-head .num{background:var(--lsurface2);color:var(--lmuted);}
.work-light details summary{color:var(--lmuted);}
.work-light details summary:hover{color:var(--ltext);}
.work-light pre.out{background:var(--lbg);border:1px solid var(--lborder);color:var(--ltext);}
.work-light .step-result{background:var(--lbg);border:1px solid var(--lborder);}
.work-light .batch-thumb{background:var(--lbg);border:1px solid var(--lborder);}
.work-light .result-meta{color:var(--lmuted);}
.work-light .ck{color:var(--ltext);}
.work-light .docs-verb{background:var(--lbg);border:1px solid var(--lborder);}
.work-light .cap-table td{border:1px solid var(--lborder);}
.work-light .cap-table td:first-child{color:var(--lmuted);}
.work-light .placeholder{color:var(--lmuted);}

/* ══ Screenshot viewer (item 3) — light, framed, scrollable; checkerboard backdrop ══ */
.shot-viewer{border:1px solid var(--lborder);border-radius:var(--radius);background:#fff;
  background-image:linear-gradient(45deg,#e8e8e8 25%,transparent 25%),linear-gradient(-45deg,#e8e8e8 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#e8e8e8 75%),linear-gradient(-45deg,transparent 75%,#e8e8e8 75%);
  background-size:18px 18px;background-position:0 0,0 9px,9px -9px,-9px 0;
  max-height:60vh;overflow:auto;padding:8px;}
.shot-viewer img{display:block;max-width:100%;height:auto;}
.shot-bar{display:flex;gap:8px;margin-top:6px;}
.shot-bar a{font-size:.74rem;text-decoration:none;color:var(--accent);border:1px solid var(--lborder);
  border-radius:6px;padding:4px 10px;cursor:pointer;background:var(--lbg);}
.shot-bar a:hover{border-color:var(--accent);}

/* ══ Bottom console pane (item 6) — light __tool REPL ══ */
#console-pane{display:flex;flex-direction:column;gap:8px;padding:12px;overflow:auto;}
#console-input{width:100%;min-height:80px;font-family:monospace;font-size:.8rem;
  background:var(--lbg);border:1px solid var(--lborder);border-radius:var(--radius);color:var(--ltext);padding:8px;resize:vertical;}
#console-out{flex:1;min-height:60px;}
.console-quick{display:flex;gap:6px;flex-wrap:wrap;}

/* ══ Resizable work area (item 2). Three light panes (builder | result over a
      full-width console) laid out with a CSS grid; two drag handles resize the
      column split and the console height. Pure in-house — no external component,
      so it always renders. Sizes persist to localStorage. ══ */
.console-grid{flex:1;display:grid;
  grid-template-columns: var(--lc,1fr) 6px var(--rc,1fr);
  grid-template-rows: var(--tr,1fr) 6px var(--cr,260px);
  grid-template-areas:"builder vsplit result" "hsplit hsplit hsplit" "console console console";
  overflow:hidden;min-height:0;}
.console-grid #builder{grid-area:builder;min-width:0;min-height:0;overflow:auto;}
.console-grid #result-panel{grid-area:result;min-width:0;min-height:0;overflow:auto;}
.console-grid #console-pane{grid-area:console;min-height:0;overflow:auto;border-top:1px solid var(--lborder);}
.vsplit{grid-area:vsplit;cursor:col-resize;background:var(--lborder);}
.hsplit{grid-area:hsplit;cursor:row-resize;background:var(--lborder);}
.vsplit:hover,.hsplit:hover{background:var(--accent);}
</style>
</head>
<body>

<header>
  <h1>SG <span>Playwright</span> Console</h1>
  <span id="health-badge" class="badge chk">checking…</span>
  <span id="svc-info" style="font-size:.72rem;color:var(--muted)"></span>
  <nav>
    <a id="docs-link" target="_blank">API docs ↗</a>
    <a id="skills-link" target="_blank">Skills ↗</a>
    <a onclick="switchTab('service')">Service ⚙</a>
  </nav>
</header>

<!-- auth-mode toggle (Decision #7) -->
<div class="authbar">
  <label>Auth mode</label>
  <div class="tg" id="auth-tg">
    <button id="am-apikey" class="active" onclick="setAuthMode('apiKey')">X-API-Key (direct)</button>
    <button id="am-proxy"  onclick="setAuthMode('proxy')">x-sgraph-access-token (/pw)</button>
  </div>
  <div class="kr">
    <label for="api-key" style="white-space:nowrap;">Key/Token</label>
    <input id="api-key" type="password" placeholder="leave blank if not required">
    <button class="ib" onclick="toggleKeyVis()" title="Show/hide">👁</button>
  </div>
  <span class="keynote" title="The key is stored unencrypted in this browser's localStorage. Acceptable for a dev tool; clear it on shared machines.">⚠ stored cleartext in localStorage</span>
</div>

<main>
  <!-- tab rail: 1:1 with endpoint families (Decision #5) -->
  <div class="tab-rail" id="tab-rail">
    <button data-tab="screenshot" class="active" onclick="switchTab('screenshot')">Screenshot</button>
    <button data-tab="sequence" onclick="switchTab('sequence')">Sequence</button>
    <button data-tab="inspect"  onclick="switchTab('inspect')">Inspect</button>
    <button data-tab="session"  onclick="switchTab('session')">Session</button>
    <button data-tab="browser"  onclick="switchTab('browser')">Browser</button>
    <button data-tab="debug"    onclick="switchTab('debug')">Debug</button>
    <button data-tab="service"  onclick="switchTab('service')">Service</button>
    <button data-tab="docs"     onclick="switchTab('docs')">Docs</button>
  </div>

  <!-- work-area: in-house resizable CSS grid — builder | result over a full-width
       console, with drag handles (#vsplit/#hsplit). Light panes per Decision #1. -->
  <div class="console-grid" id="work-area">
    <!-- ────────── BUILDER (left of split) — light work pane ────────── -->
    <div class="builder work-light" id="builder">

      <!-- Screenshot tab -->
      <div id="tab-screenshot" class="tab-pane active">
        <div class="tg" style="flex:0 0 auto;width:fit-content;">
          <button id="ss-single" class="active" onclick="setSsMode('single')">Single</button>
          <button id="ss-batch" onclick="setSsMode('batch')">Batch</button>
        </div>

        <div id="ss-single-pane">
          <div><label>URL</label><input id="ss-url" type="text" value="https://sgraph.ai"></div>
          <div>
            <label>Render</label>
            <div class="tg">
              <button id="fmt-png" class="active" onclick="setFmt('png')">Image (PNG)</button>
              <button id="fmt-html" onclick="setFmt('html')">HTML source</button>
            </div>
          </div>
          <details>
            <summary>▸ Advanced options</summary>
            <div class="db">
              <div><label>JavaScript expression (runs before capture — uses the screenshot allow_all runner, not the gated evaluate verb)</label>
                <textarea id="ss-js" rows="2" placeholder="document.body.style.zoom='80%'"></textarea></div>
              <div><label>Click selector (before capture)</label>
                <input id="ss-click" type="text" placeholder="button#accept-cookies"></div>
              <div class="ck"><input id="ss-full" type="checkbox"><label for="ss-full">Full-page screenshot</label></div>
            </div>
          </details>
        </div>

        <div id="ss-batch-pane" style="display:none">
          <div class="tg" style="width:fit-content;">
            <button id="bm-items" class="active" onclick="setBatchMode('items')">Independent sessions</button>
            <button id="bm-steps" onclick="setBatchMode('steps')">Sequential steps</button>
          </div>
          <div id="sps-row" class="ck" style="display:none"><input id="sps-chk" type="checkbox" checked><label for="sps-chk">Screenshot after each step</label></div>
          <div id="ss-cards" style="display:flex;flex-direction:column;gap:8px;"></div>
          <button class="add-btn" onclick="addCard()">+ Add URL</button>
        </div>

        <div class="btn-row">
          <button class="exec-btn" id="btn-ss" onclick="execScreenshot()">Execute</button>
          <button class="gbtn" onclick="copyCurl()">Copy as curl</button>
          <button class="gbtn" onclick="copyJson()">Copy as JSON</button>
        </div>
        <div class="sr"><span id="spin-ss" style="display:none" class="spin"></span><span id="status-ss"></span></div>
      </div>

      <!-- Sequence tab (the 24-verb builder) -->
      <div id="tab-sequence" class="tab-pane">
        <div class="section-title">Sequence builder → POST /sequence/execute</div>
        <div id="seq-steps" style="display:flex;flex-direction:column;gap:8px;"></div>
        <div class="btn-row">
          <select id="seq-add-verb"></select>
          <button class="add-btn" onclick="seqAddStep()">+ Add step</button>
        </div>
        <details>
          <summary>▸ Capture / config</summary>
          <div class="db">
            <div><label>Screenshot sink (limited to deployment's supported_sinks)</label>
              <select id="seq-sink"></select></div>
            <div class="ck"><input id="seq-shot-enabled" type="checkbox" checked><label for="seq-shot-enabled">capture_config.screenshot.enabled (needed for inline_b64)</label></div>
            <div class="ck"><input id="seq-pdf-enabled" type="checkbox"><label for="seq-pdf-enabled">capture_config.pdf.enabled</label></div>
          </div>
        </details>
        <div class="btn-row">
          <button class="exec-btn" id="btn-seq" onclick="execSequence()">Execute</button>
          <button class="gbtn" onclick="copyCurl()">Copy as curl</button>
          <button class="gbtn" onclick="copyJson()">Copy as JSON</button>
        </div>
        <div class="sr"><span id="spin-seq" style="display:none" class="spin"></span><span id="status-seq"></span></div>
      </div>

      <!-- Inspect tab -->
      <div id="tab-inspect" class="tab-pane">
        <div class="section-title">Inspect → POST /inspect (snapshot-once, probe-many)</div>
        <div><label>navigate.url</label><input id="ins-url" type="text" value="https://sgraph.ai"></div>
        <div class="ck"><input id="ins-settle" type="checkbox" checked><label for="ins-settle">settle: wait_for networkidle</label></div>
        <div class="ck"><input id="ins-diag" type="checkbox" checked><label for="ins-diag">diagnostics_on_fail</label></div>
        <div class="section-title">Probes (read-only verbs only)</div>
        <div id="ins-probes" style="display:flex;flex-direction:column;gap:8px;"></div>
        <div class="btn-row">
          <select id="ins-add-verb"></select>
          <button class="add-btn" onclick="insAddProbe()">+ Add probe</button>
        </div>
        <div class="btn-row">
          <button class="exec-btn" id="btn-ins" onclick="execInspect()">Execute</button>
          <button class="gbtn" onclick="copyCurl()">Copy as curl</button>
          <button class="gbtn" onclick="copyJson()">Copy as JSON</button>
        </div>
        <div class="sr"><span id="spin-ins" style="display:none" class="spin"></span><span id="status-ins"></span></div>
      </div>

      <!-- Session tab -->
      <div id="tab-session" class="tab-pane">
        <div class="section-title">Session → /session/open|act|probe|close (stateful)</div>
        <div id="sess-disabled" class="hint" style="display:none">This deployment reports supports_persistent=false — Session is unavailable here.</div>
        <div class="result-meta">Active session: <strong id="sess-id">none</strong> <span id="sess-exp"></span></div>
        <div class="btn-row">
          <button class="gbtn" id="sess-open" onclick="sessOpen()">open</button>
          <button class="gbtn" id="sess-act" onclick="sessAct()">act (run current Sequence)</button>
          <button class="gbtn" id="sess-probe" onclick="sessProbe()">probe (run current Inspect probes)</button>
          <button class="gbtn" id="sess-close" onclick="sessClose()">close</button>
        </div>
        <div class="hint" style="color:var(--muted);background:var(--surface2);border-color:var(--border)">act uses the Sequence-tab steps; probe uses the Inspect-tab probes (no navigate). Page state persists across calls.</div>
        <div class="sr"><span id="spin-sess" style="display:none" class="spin"></span><span id="status-sess"></span></div>
      </div>

      <!-- Browser tab -->
      <div id="tab-browser" class="tab-pane">
        <div class="section-title">Browser one-shots → POST /browser/*</div>
        <div><label>verb</label>
          <select id="br-verb" onchange="brRenderFields()">
            <option value="navigate">navigate</option>
            <option value="click">click</option>
            <option value="fill">fill</option>
            <option value="get-content">get-content</option>
            <option value="get-url">get-url</option>
            <option value="screenshot">screenshot</option>
          </select></div>
        <div id="br-fields" style="display:flex;flex-direction:column;gap:8px;"></div>
        <div class="btn-row">
          <button class="exec-btn" id="btn-br" onclick="execBrowser()">Execute</button>
          <button class="gbtn" onclick="copyCurl()">Copy as curl</button>
          <button class="gbtn" onclick="copyJson()">Copy as JSON</button>
        </div>
        <div class="sr"><span id="spin-br" style="display:none" class="spin"></span><span id="status-br"></span></div>
      </div>

      <!-- Debug tab -->
      <div id="tab-debug" class="tab-pane">
        <div class="section-title">Debug → /inspect with console + network probes</div>
        <div><label>URL</label><input id="dbg-url" type="text" value="https://example.com"></div>
        <div><label>console tail lines</label><input id="dbg-lines" type="number" value="200"></div>
        <div class="ck"><input id="dbg-shot" type="checkbox" checked><label for="dbg-shot">also capture a full-page screenshot probe</label></div>
        <div class="btn-row">
          <button class="exec-btn" id="btn-dbg" onclick="execDebug()">Run diagnostics</button>
          <button class="gbtn" onclick="copyCurl()">Copy as curl</button>
          <button class="gbtn" onclick="copyJson()">Copy as JSON</button>
        </div>
        <div class="sr"><span id="spin-dbg" style="display:none" class="spin"></span><span id="status-dbg"></span></div>
      </div>

      <!-- Service tab -->
      <div id="tab-service" class="tab-pane">
        <div class="section-title">Service — health / info / capabilities / metrics</div>
        <div class="btn-row">
          <button class="gbtn" onclick="svcLoad('/health/info')">/health/info</button>
          <button class="gbtn" onclick="svcLoad('/health/status')">/health/status</button>
          <button class="gbtn" onclick="svcLoad('/health/capabilities')">/health/capabilities</button>
          <button class="gbtn" onclick="svcMetrics()">/metrics</button>
        </div>
        <div id="svc-caps"></div>
        <a id="cookie-link" target="_blank" style="font-size:.78rem;color:var(--accent);text-decoration:none">Set-cookie helper ↗</a>
      </div>

      <!-- Docs tab -->
      <div id="tab-docs" class="tab-pane">
        <div class="section-title">In-app reference (generated from live /health/capabilities + the capability surface)</div>
        <div id="docs-content"></div>
      </div>

    </div>

    <!-- ────────── RESULT (right of split) — light work pane ────────── -->
    <div class="result work-light" id="result-panel">
      <!-- gallery + workflow IO live in the result column header so every builder shares them -->
      <details open>
        <summary>▸ Example gallery (S1–S5 self-contained · W1–W9) &amp; workflow import/export</summary>
        <div class="db">
          <div class="btn-row">
            <button class="gbtn" onclick="wfSaveLocal()">Save</button>
            <button class="gbtn" onclick="wfLoadLocal()">Load</button>
            <button class="gbtn" onclick="wfExportFile()">Export ↓</button>
            <button class="gbtn" onclick="document.getElementById('wf-file').click()">Import ↑</button>
            <input id="wf-file" type="file" accept="application/json" style="display:none" onchange="wfImportFile(event)">
          </div>
          <div class="gallery" id="gallery"></div>
        </div>
      </details>
      <div class="result-meta" id="result-meta" style="display:none"></div>
      <img id="result-img" alt="result">
      <pre id="result-html" class="out" style="display:none"></pre>
      <div id="result-steps"></div>
      <div id="batch-grid" class="batch-grid"></div>
      <pre id="result-err"></pre>
      <p class="placeholder" id="placeholder">Build a request and click Execute</p>
    </div>

    <!-- ────────── CONSOLE (bottom dock) — light __tool REPL (item 6) ────────── -->
    <div id="console-pane" class="work-light">
      <div class="section-title">window.__tool console — runs in YOUR browser (not the server-side evaluate allowlist)</div>
      <div class="console-quick">
        <button class="gbtn" onclick="consoleQuick('await __tool.meta.getMethods()')">List methods</button>
        <button class="gbtn" onclick="consoleQuick('await __tool.meta.getManifest()')">Manifest</button>
        <button class="gbtn" onclick="consoleQuick('await __tool.meta.getSkills()')">Skills</button>
        <button class="gbtn" onclick="consoleQuick('await __tool.meta.getLog()')">Log</button>
      </div>
      <textarea id="console-input" spellcheck="false" placeholder="await __tool.screenshot({url: window.location.origin + window.API_BASE + '/test-pages/simple'})  —  Ctrl/Cmd+Enter to run"></textarea>
      <div class="btn-row"><button class="exec-btn" id="btn-console" onclick="consoleRun()">Run ▶</button></div>
      <div id="console-out"></div>
    </div>

    <!-- drag handles — resize the builder|result column split and the console height (item 2) -->
    <div class="vsplit" id="vsplit" title="Drag to resize"></div>
    <div class="hsplit" id="hsplit" title="Drag to resize"></div>
  </div>
</main>

<script>
// ════════════════════════════════════════════════════════════════════════════
//  Capability surface — the SINGLE source of truth for verbs/fields. Mirrors the
//  code-derived capability map (06/21/15/playwright-capability-map.md §3) and
//  sg-playwright-capabilities/SKILL.md. Field names match the real Schema__* — no
//  invented names (Decision #9). Docs (P4) + getSkills().api (P5) generate from this.
// ════════════════════════════════════════════════════════════════════════════
const ENUMS = {
  wait_until:  ['load','domcontentloaded','networkidle'],
  button:      ['left','right','middle'],
  key:         ['Enter','Tab','Escape','Backspace','Delete','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Control+a','Control+c','Control+v'],
  codec:       ['webm','mp4'],
  return_type: ['json','string','number','boolean'],
  content_format: ['html','text'],
};
// verb → field specs. {name, type, def, req, enum, hint}
const VERBS = {
  navigate:       [{n:'url',req:1},{n:'wait_until',enum:'wait_until',def:'load'},{n:'referer'}],
  click:          [{n:'selector',req:1},{n:'button',enum:'button',def:'left'},{n:'click_count',type:'number',def:1},{n:'delay_ms',type:'number',def:0},{n:'force',type:'bool',def:false}],
  fill:           [{n:'selector',req:1},{n:'value',req:1},{n:'clear_first',type:'bool',def:true}],
  press:          [{n:'selector'},{n:'key',req:1,enum:'key'}],
  select:         [{n:'selector',req:1},{n:'values',type:'list',req:1}],
  hover:          [{n:'selector',req:1}],
  scroll:         [{n:'selector'},{n:'x',type:'number',def:0},{n:'y',type:'number',def:0}],
  wait:           [{n:'duration_ms',type:'number',def:0}],
  wait_for:       [{n:'selector'},{n:'text'},{n:'url_pattern'},{n:'state',enum:'wait_until'},{n:'function',hint:'needs server JS allowlist'},{n:'network_idle_ms',type:'number'},{n:'visible',type:'bool',def:true},{n:'selector_gone',type:'bool',def:false}],
  screenshot:     [{n:'full_page',type:'bool',def:false},{n:'selector'},{n:'save_as'},{n:'frame_selector'}],
  set_viewport:   [{n:'viewport',type:'viewport',req:1}],
  evaluate:       [{n:'expression',req:1,hint:'allowlist-gated — default deny-all reports failed/partial, NOT 422'},{n:'return_type',enum:'return_type',def:'json'}],
  dispatch_event: [{n:'selector',req:1},{n:'event_type',req:1},{n:'event_init',type:'json'}],
  video_start:    [{n:'codec',enum:'codec',def:'webm'},{video:1}],
  video_stop:     [{n:'save_as'},{video:1}],
  get_content:    [{n:'selector'},{n:'content_format',enum:'content_format',def:'html'},{n:'inline_in_response',type:'bool',def:true}],
  get_url:        [],
  get_text:       [{n:'selector'},{n:'inline_in_response',type:'bool',def:true}],
  get_html:       [{n:'selector'},{n:'inline_in_response',type:'bool',def:true}],
  get_dom_tree:   [{n:'root_selector'},{n:'max_depth',type:'number',def:8},{n:'include_invisible',type:'bool',def:false}],
  get_a11y_tree:  [{n:'root_selector'},{n:'interesting_only',type:'bool',def:true}],
  get_pdf:        [{n:'format',def:'A4'},{n:'landscape',type:'bool',def:false},{n:'print_background',type:'bool',def:true}],
  get_console_tail:[{n:'lines',type:'number',def:100}],
  get_network_failures: [],
};
const VERB_LIST = Object.keys(VERBS);                                                // 24 verbs, capability-map order
const PROBE_VERBS = ['get_url','get_text','get_html','get_dom_tree','get_a11y_tree','screenshot','get_console_tail','get_network_failures'];

// ════════════════════════════════════════════════════════════════════════════
//  Auth (Decision #7) — single source for every request incl. the health badge.
// ════════════════════════════════════════════════════════════════════════════
const KEY_LS = 'sg_playwright_api_key', MODE_LS = 'sg_playwright_auth_mode';
let authMode = localStorage.getItem(MODE_LS) || 'apiKey';                            // 'apiKey' | 'proxy'
const keyEl = document.getElementById('api-key');
keyEl.value = localStorage.getItem(KEY_LS) || '';
let _saveT; keyEl.addEventListener('input', () => { clearTimeout(_saveT); _saveT = setTimeout(() => localStorage.setItem(KEY_LS, keyEl.value), 300); });
function toggleKeyVis(){ keyEl.type = keyEl.type === 'password' ? 'text' : 'password'; }
function authHeaderName(){ return authMode === 'proxy' ? 'x-sgraph-access-token' : 'X-API-Key'; }
function authHeaders(extra){
  const h = Object.assign({}, extra || {});
  const k = keyEl.value.trim();
  if (k) h[authHeaderName()] = k;
  return h;
}
function setAuthMode(m){
  authMode = m; localStorage.setItem(MODE_LS, m);
  document.getElementById('am-apikey').classList.toggle('active', m==='apiKey');
  document.getElementById('am-proxy').classList.toggle('active', m==='proxy');
  bootstrap();
}
function setAuth(opts){                                                              // window.__tool.setAuth — never logs the token
  if (opts && opts.authMode) setAuthMode(opts.authMode === 'proxy' ? 'proxy' : 'apiKey');
  if (opts && typeof opts.token === 'string') { keyEl.value = opts.token; localStorage.setItem(KEY_LS, opts.token); }
}

function escHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

// ── copyText (item 4 — real bug): navigator.clipboard is undefined on insecure
//    origins like http://0.0.0.0, so the old bare clipboard calls threw silently
//    (TypeError: cannot read writeText of undefined). Prefer the async Clipboard API
//    when available + secure; else
//    fall back to a hidden <textarea> + execCommand('copy'). Never throws. ──
function copyText(s){
  s = String(s == null ? '' : s);
  try{
    if (navigator.clipboard && window.isSecureContext){
      navigator.clipboard.writeText(s).catch(()=>_copyFallback(s));
      return true;
    }
  }catch(e){}
  return _copyFallback(s);
}
function _copyFallback(s){
  try{
    const ta=document.createElement('textarea'); ta.value=s;
    ta.style.position='fixed'; ta.style.opacity='0'; ta.style.left='-9999px';
    document.body.appendChild(ta); ta.focus(); ta.select();
    let ok=false; try{ ok=document.execCommand('copy'); }catch(e){ ok=false; }
    document.body.removeChild(ta); return ok;
  }catch(e){ return false; }
}

// ── request() — reads status BEFORE parsing; falls back to text() on non-JSON ──
async function apiGet(path){ return fetch(window.API_BASE + path, { headers: authHeaders() }); }
async function request(method, path, body){
  const headers = authHeaders(body !== undefined ? {'Content-Type':'application/json'} : {});
  const opts = { method, headers };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(window.API_BASE + path, opts);
  let data, raw = await r.text();
  try { data = JSON.parse(raw); } catch { data = raw; }
  return { ok:r.ok, status:r.status, data, headers:r.headers };
}

// ════════════════════════════════════════════════════════════════════════════
//  Tabs
// ════════════════════════════════════════════════════════════════════════════
let activeTab = 'screenshot';
function switchTab(t){
  activeTab = t;
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === 'tab-'+t));
  document.querySelectorAll('.tab-rail button').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
  if (t === 'docs') renderDocs();
  if (t === 'service') renderCapsTable();
}

// ════════════════════════════════════════════════════════════════════════════
//  Screenshot tab
// ════════════════════════════════════════════════════════════════════════════
let ssMode = 'single', fmt = 'png', batchMode = 'items', cardId = 0;
const cardData = {};
function setSsMode(m){ ssMode=m; document.getElementById('ss-single').classList.toggle('active',m==='single');
  document.getElementById('ss-batch').classList.toggle('active',m==='batch');
  document.getElementById('ss-single-pane').style.display = m==='single'?'block':'none';
  document.getElementById('ss-batch-pane').style.display  = m==='batch'?'block':'none'; }
function setFmt(f){ fmt=f; document.getElementById('fmt-png').classList.toggle('active',f==='png');
  document.getElementById('fmt-html').classList.toggle('active',f==='html'); }
function setBatchMode(m){ batchMode=m; document.getElementById('bm-items').classList.toggle('active',m==='items');
  document.getElementById('bm-steps').classList.toggle('active',m==='steps');
  document.getElementById('sps-row').style.display = m==='steps'?'flex':'none'; reNumberCards(); }
function addCard(url=''){
  const id = ++cardId;
  const div = document.createElement('div'); div.className='step-card'; div.dataset.id=id;
  div.innerHTML = `<div class="step-head"><span class="num"></span>
      <input type="text" value="${escHtml(url)}" placeholder="https://…" oninput="cardField(${id},'url',this.value)">
      <button class="rm-btn" onclick="removeCard(${id})">×</button></div>
    <div class="step-fields">
      <div class="tg" style="width:fit-content"><button class="active" onclick="cardFmt(${id},'png',this)">PNG</button><button onclick="cardFmt(${id},'html',this)">HTML</button></div>
      <input type="text" placeholder="JS expression…" oninput="cardField(${id},'javascript',this.value)">
      <input type="text" placeholder="click selector…" oninput="cardField(${id},'click',this.value)">
      <label class="ck"><input type="checkbox" onchange="cardField(${id},'full_page',this.checked)"><span>Full-page</span></label>
    </div>`;
  document.getElementById('ss-cards').appendChild(div);
  cardData[id] = {url, format:'png'}; reNumberCards();
}
function cardField(id,key,val){ if(!cardData[id])cardData[id]={format:'png'};
  if(val===''||val===false) delete cardData[id][key]; else cardData[id][key]=val; }
function cardFmt(id,f,btn){ btn.parentElement.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active'); cardData[id].format=f; }
function removeCard(id){ const el=document.querySelector(`.step-card[data-id="${id}"]`); if(el)el.remove(); delete cardData[id]; reNumberCards(); }
function reNumberCards(){ const isSteps=batchMode==='steps';
  document.querySelectorAll('#ss-cards .step-card').forEach((el,i)=>{ el.querySelector('.num').textContent = isSteps?`step ${i+1}`:`#${i+1}`; }); }
function getCardItems(){
  return [...document.querySelectorAll('#ss-cards .step-card')].map(el=>{
    const id=el.dataset.id; const url=el.querySelector('input[type=text]').value.trim()||null;
    const d={...(cardData[id]||{}),url}; const out={url:d.url,format:d.format||'png'};
    if(d.javascript)out.javascript=d.javascript; if(d.click)out.click=d.click; if(d.full_page)out.full_page=true;
    return out;
  });
}
function buildScreenshotBody(){
  if (ssMode==='single'){
    const url=document.getElementById('ss-url').value.trim();
    const body={url, format:fmt};
    const js=document.getElementById('ss-js').value.trim(); if(js)body.javascript=js;
    const click=document.getElementById('ss-click').value.trim(); if(click)body.click=click;
    if(document.getElementById('ss-full').checked) body.full_page=true;
    return {path:'/screenshot', body};
  }
  const isSteps=batchMode==='steps'; const all=getCardItems();
  const items=isSteps?all:all.filter(x=>x.url);
  const body = isSteps ? {steps:items, screenshot_per_step:document.getElementById('sps-chk').checked} : {items};
  return {path:'/screenshot/batch', body};
}
async function execScreenshot(){
  const {path,body}=buildScreenshotBody();
  if(ssMode==='single' && !body.url){ setStatus('ss','⚠ URL required',true); return; }
  if(ssMode==='batch' && !((body.items&&body.items.length)||(body.steps&&body.steps.length))){ setStatus('ss','⚠ add a URL',true); return; }
  await runRequest('ss', 'POST', path, body, res => {
    if(path==='/screenshot'){ renderSingle(res.data, fmt); }
    else renderBatch(res.data, body.items||body.steps||[]);
  });
}

// ════════════════════════════════════════════════════════════════════════════
//  Step builders (Sequence + Inspect probes share field rendering)
// ════════════════════════════════════════════════════════════════════════════
let seqStepId = 0, insProbeId = 0;
const seqData = {}, insData = {};
function fieldInput(scope, id, verb, f){
  const key = f.n;
  const fid = `${scope}-${id}-${key}`;
  if (f.enum){
    const opts = ENUMS[f.enum].map(v=>`<option ${v===f.def?'selected':''}>${v}</option>`).join('');
    return `<div class="fr"><label>${key}${f.req?' *':''}</label><select id="${fid}" onchange="stepField('${scope}',${id},'${key}',this.value)">${opts}</select></div>`;
  }
  if (f.type==='bool'){
    return `<div class="fr"><label class="ck"><input type="checkbox" id="${fid}" ${f.def?'checked':''} onchange="stepField('${scope}',${id},'${key}',this.checked)"><span>${key}</span></label></div>`;
  }
  if (f.type==='viewport'){
    return `<div class="fr"><label>${key} *</label><div style="display:flex;gap:6px"><input type="number" placeholder="width" oninput="vpField('${scope}',${id},'width',this.value)"><input type="number" placeholder="height" oninput="vpField('${scope}',${id},'height',this.value)"></div></div>`;
  }
  const ph = f.type==='list' ? 'comma,separated,values' : (f.type==='json' ? '{"k":"v"}' : (f.def!==undefined?String(f.def):''));
  const hint = f.hint ? `<div class="hint">⚠ ${escHtml(f.hint)}</div>` : '';
  return `<div class="fr"><label>${key}${f.req?' *':''}</label><input type="text" id="${fid}" placeholder="${escHtml(ph)}" oninput="stepField('${scope}',${id},'${key}',this.value)">${hint}</div>`;
}
function stepField(scope,id,key,val){
  const store = scope==='seq'?seqData:insData;
  if(!store[id]) store[id]={};
  if(val===''||val===false||val===null) delete store[id][key]; else store[id][key]=val;
}
function vpField(scope,id,axis,val){
  const store = scope==='seq'?seqData:insData;
  if(!store[id]) store[id]={};
  if(!store[id].viewport) store[id].viewport={};
  if(val==='') delete store[id].viewport[axis]; else store[id].viewport[axis]=Number(val);
}
function renderVerbFields(scope,id,verb){
  return VERBS[verb].filter(f=>f.n).map(f=>fieldInput(scope,id,verb,f)).join('');
}
function coerceStep(verb, raw){
  const out = {action: verb};
  for (const f of VERBS[verb]){
    if(!f.n) continue;
    let v = raw[f.n];
    if (v===undefined || v==='') continue;
    if (f.type==='number') v = Number(v);
    else if (f.type==='list') v = String(v).split(',').map(s=>s.trim()).filter(Boolean);
    else if (f.type==='json'){ try{ v = JSON.parse(v); }catch{} }
    out[f.n] = v;
  }
  if (raw.viewport) out.viewport = raw.viewport;
  return out;
}

// ── Sequence tab ──
function seqAddStep(verb){
  verb = verb || document.getElementById('seq-add-verb').value;
  const id = ++seqStepId;
  const div = document.createElement('div'); div.className='step-card'; div.dataset.id=id; div.dataset.verb=verb;
  div.innerHTML = `<div class="step-head"><span class="num"></span><strong style="flex:1;color:var(--accent);font-size:.8rem">${escHtml(verb)}</strong>
      <button class="mv-btn" onclick="seqMove(${id},-1)">↑</button><button class="mv-btn" onclick="seqMove(${id},1)">↓</button>
      <button class="rm-btn" onclick="seqRemove(${id})">×</button></div>
    <div class="step-fields">${renderVerbFields('seq',id,verb)}</div>`;
  document.getElementById('seq-steps').appendChild(div);
  seqData[id] = {};
  seqRenumber();
}
function seqRemove(id){ const el=document.querySelector(`#seq-steps .step-card[data-id="${id}"]`); if(el)el.remove(); delete seqData[id]; seqRenumber(); }
function seqMove(id,dir){ const el=document.querySelector(`#seq-steps .step-card[data-id="${id}"]`); if(!el)return;
  const sib = dir<0 ? el.previousElementSibling : el.nextElementSibling; if(!sib)return;
  if(dir<0) el.parentNode.insertBefore(el,sib); else el.parentNode.insertBefore(sib,el); seqRenumber(); }
function seqRenumber(){ document.querySelectorAll('#seq-steps .step-card').forEach((el,i)=>el.querySelector('.num').textContent=i+1); }
function buildSequenceBody(){
  const steps = [...document.querySelectorAll('#seq-steps .step-card')].map(el=>coerceStep(el.dataset.verb, seqData[el.dataset.id]||{}));
  const capture = {};
  if(document.getElementById('seq-shot-enabled').checked) capture.screenshot = {enabled:true, sink:(document.getElementById('seq-sink').value||'inline')};
  if(document.getElementById('seq-pdf-enabled').checked)  capture.pdf        = {enabled:true, sink:(document.getElementById('seq-sink').value||'inline')};
  const body = {steps};
  if(Object.keys(capture).length) body.capture_config = capture;
  return {path:'/sequence/execute', body};
}
async function execSequence(){
  const {path,body}=buildSequenceBody();
  if(!body.steps.length){ setStatus('seq','⚠ add at least one step',true); return; }
  await runRequest('seq','POST',path,body, res => renderSequence(res.data));
}

// ── Inspect tab ──
function insAddProbe(verb){
  verb = verb || document.getElementById('ins-add-verb').value;
  const id = ++insProbeId;
  const div = document.createElement('div'); div.className='step-card'; div.dataset.id=id; div.dataset.verb=verb;
  div.innerHTML = `<div class="step-head"><span class="num"></span>
      <input type="text" placeholder="probe name" value="${escHtml(verb)}" oninput="insName(${id},this.value)" style="flex:1">
      <strong style="color:var(--muted);font-size:.72rem">${escHtml(verb)}</strong>
      <button class="rm-btn" onclick="insRemove(${id})">×</button></div>
    <div class="step-fields">${renderVerbFields('ins',id,verb)}</div>`;
  document.getElementById('ins-probes').appendChild(div);
  insData[id] = {}; insNames[id] = verb;
}
const insNames = {};
function insName(id,v){ insNames[id]=v; }
function insRemove(id){ const el=document.querySelector(`#ins-probes .step-card[data-id="${id}"]`); if(el)el.remove(); delete insData[id]; delete insNames[id]; }
function buildInspectBody(){
  const url=document.getElementById('ins-url').value.trim();
  const probes={};
  [...document.querySelectorAll('#ins-probes .step-card')].forEach(el=>{
    const id=el.dataset.id; const name=(insNames[id]||el.dataset.verb).trim()||el.dataset.verb;
    probes[name]=coerceStep(el.dataset.verb, insData[id]||{});
  });
  const body={ navigate:{url}, settle: document.getElementById('ins-settle').checked?[{action:'wait_for',state:'networkidle'}]:[],
               probes, diagnostics_on_fail: document.getElementById('ins-diag').checked };
  return {path:'/inspect', body};
}
async function execInspect(){
  const {path,body}=buildInspectBody();
  if(!body.navigate.url){ setStatus('ins','⚠ navigate.url required',true); return; }
  await runRequest('ins','POST',path,body, res => renderInspect(res.data));
}

// ── Session tab ──
let sessionId = null;
function buildSessionMeta(){ const el=document.getElementById('sess-id'); el.textContent = sessionId || 'none'; }
async function sessOpen(){
  await runRequest('sess','POST','/session/open',{browser_config:{}}, res=>{
    sessionId = res.data && res.data.session_id || null; buildSessionMeta();
    document.getElementById('sess-exp').textContent = res.data && res.data.expires_in_ms ? `expires in ${res.data.expires_in_ms}ms` : '';
    renderJson(res.data);
  });
}
async function sessAct(){
  if(!sessionId){ setStatus('sess','⚠ open a session first',true); return; }
  const {body}=buildSequenceBody();
  await runRequest('sess','POST',`/session/${encodeURIComponent(sessionId)}/act`,body, res=>renderSequence(res.data));
}
async function sessProbe(){
  if(!sessionId){ setStatus('sess','⚠ open a session first',true); return; }
  const {body}=buildInspectBody(); delete body.navigate;                            // probe is inspect-shape WITHOUT navigate (page state persists)
  await runRequest('sess','POST',`/session/${encodeURIComponent(sessionId)}/probe`,body, res=>renderInspect(res.data));
}
async function sessClose(){
  if(!sessionId){ setStatus('sess','⚠ no open session',true); return; }
  const sid=sessionId;
  await runRequest('sess','POST',`/session/${encodeURIComponent(sid)}/close`,undefined, res=>{ sessionId=null; buildSessionMeta(); document.getElementById('sess-exp').textContent=''; renderJson(res.data); });
}

// ── Browser tab ──
const BROWSER_FIELDS = {
  navigate:      [{n:'url',req:1}],
  click:         [{n:'url',req:1},{n:'selector',req:1}],
  fill:          [{n:'url',req:1},{n:'selector',req:1},{n:'value',req:1}],
  'get-content': [{n:'url',req:1}],
  'get-url':     [{n:'url',req:1}],
  screenshot:    [{n:'url',req:1},{n:'full_page',type:'bool'}],
};
const brData = {};
function brRenderFields(){
  const verb=document.getElementById('br-verb').value;
  const wrap=document.getElementById('br-fields'); brData[verb]=brData[verb]||{};
  wrap.innerHTML = BROWSER_FIELDS[verb].map(f=>{
    if(f.type==='bool') return `<label class="ck"><input type="checkbox" onchange="brData['${verb}']['${f.n}']=this.checked"><span>${f.n}</span></label>`;
    return `<div class="fr"><label>${f.n}${f.req?' *':''}</label><input type="text" value="${f.n==='url'?'https://sgraph.ai':''}" oninput="brData['${verb}']['${f.n}']=this.value"></div>`;
  }).join('');
  if(BROWSER_FIELDS[verb].some(f=>f.n==='url')) brData[verb].url = brData[verb].url||'https://sgraph.ai';
}
function buildBrowserBody(){
  const verb=document.getElementById('br-verb').value; const d=brData[verb]||{};
  const body={}; for(const f of BROWSER_FIELDS[verb]){ const v=d[f.n]; if(v!==undefined&&v!=='') body[f.n]=v; }
  return {path:'/browser/'+verb, body};
}
async function execBrowser(){
  const {path,body}=buildBrowserBody();
  const verb=document.getElementById('br-verb').value;
  if(verb==='screenshot'){                                                          // returns raw image/png with X-*-Ms timing headers
    setBusy('br',true); clearResult();
    try{
      const r=await fetch(window.API_BASE+path,{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify(body)});
      if(!r.ok){ showErr(`HTTP ${r.status}\n`+escHtml(await r.text())); setBusy('br',false); return; }
      const blob=await r.blob(); showShot(URL.createObjectURL(blob), 'browser-screenshot.png');
      const meta=document.getElementById('result-meta'); meta.style.display='flex';
      meta.innerHTML = [...r.headers].filter(([k])=>/-ms$/i.test(k)).map(([k,v])=>`<span>${escHtml(k)}: <strong>${escHtml(v)}</strong></span>`).join('') || '<span>image/png</span>';
      setStatus('br','done');
    }catch(e){ showErr('Network error: '+e.message); } finally{ setBusy('br',false); }
    return;
  }
  await runRequest('br','POST',path,body, res=>renderJson(res.data));
}

// ── Debug tab ──
function buildDebugBody(){
  const url=document.getElementById('dbg-url').value.trim();
  const lines=Number(document.getElementById('dbg-lines').value)||100;
  const probes={ console:{action:'get_console_tail',lines}, failures:{action:'get_network_failures'} };
  if(document.getElementById('dbg-shot').checked) probes.shot={action:'screenshot',full_page:true};
  return {path:'/inspect', body:{navigate:{url}, settle:[], probes, diagnostics_on_fail:true}};
}
async function execDebug(){
  const {path,body}=buildDebugBody();
  if(!body.navigate.url){ setStatus('dbg','⚠ URL required',true); return; }
  await runRequest('dbg','POST',path,body, res=>renderInspect(res.data));
}

// ════════════════════════════════════════════════════════════════════════════
//  Current request — for Copy curl / Copy JSON (Decision #6) + window.__tool
// ════════════════════════════════════════════════════════════════════════════
function currentRequest(){
  switch(activeTab){
    case 'screenshot': return buildScreenshotBody();
    case 'sequence':   return buildSequenceBody();
    case 'inspect':    return buildInspectBody();
    case 'browser':    return buildBrowserBody();
    case 'debug':      return buildDebugBody();
    case 'session':    return buildSequenceBody();
    default:           return buildScreenshotBody();
  }
}
function copyJson(){ const {body}=currentRequest(); copyText(JSON.stringify(body,null,2)); flash('JSON copied'); }
function copyCurl(){
  const {path,body}=currentRequest();
  // curl uses a placeholder — NEVER the stored token (hard rule).
  const curl = `curl -X POST '${location.origin}${window.API_BASE}${path}' \\\n  -H '${authHeaderName()}: $SG_PLAYWRIGHT_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '${JSON.stringify(body)}'`;
  copyText(curl); flash('curl copied (key placeholder $SG_PLAYWRIGHT_KEY)');
}
function flash(msg){ const el=document.getElementById('status-'+statusKeyForTab()); if(el){ el.textContent=msg; el.style.color='var(--accent2)'; } }
function statusKeyForTab(){ return {screenshot:'ss',sequence:'seq',inspect:'ins',browser:'br',debug:'dbg',session:'sess'}[activeTab]||'ss'; }

// ════════════════════════════════════════════════════════════════════════════
//  Shared run + status + result rendering
// ════════════════════════════════════════════════════════════════════════════
const runLog = [];
async function runRequest(which, method, path, body, onOk){
  setBusy(which,true); clearResult();
  try{
    const res = await request(method, path, body);
    runLog.push({path, status:res.status, ts:Date.now()});                          // no token, no body persisted
    if(!res.ok){ showErr(`HTTP ${res.status}\n`+(typeof res.data==='string'?escHtml(res.data):JSON.stringify(res.data,null,2))); setStatus(which,`HTTP ${res.status}`,true); return res; }
    if(onOk) onOk(res);
    setStatus(which,'done');
    return res;
  }catch(e){ showErr('Network error: '+e.message); setStatus(which,'network error',true); }
  finally{ setBusy(which,false); }
}
function setBusy(which,on){ const btn=document.getElementById('btn-'+which); const spin=document.getElementById('spin-'+which);
  if(btn)btn.disabled=on; if(spin)spin.style.display=on?'inline-block':'none'; if(on)setStatus(which,'running…'); }
function setStatus(which,msg,warn){ const el=document.getElementById('status-'+which); if(!el)return; el.textContent=msg; el.style.color=warn?'var(--danger)':'var(--muted)'; }
function clearResult(){
  ['result-img','result-html','result-meta'].forEach(id=>document.getElementById(id).style.display='none');
  document.getElementById('result-err').style.display='none';
  document.getElementById('result-steps').innerHTML='';
  document.getElementById('batch-grid').innerHTML='';
  document.getElementById('placeholder').style.display='block';
}
function showErr(msg){ const el=document.getElementById('result-err'); el.textContent=msg; el.style.display='block'; document.getElementById('placeholder').style.display='none'; }
function showMetaLine(html){ const el=document.getElementById('result-meta'); el.innerHTML=html; el.style.display='flex'; document.getElementById('placeholder').style.display='none'; }

function renderJson(data){ const pre=document.getElementById('result-html'); pre.textContent=JSON.stringify(data,null,2); pre.style.display='block'; document.getElementById('placeholder').style.display='none'; }

// ── Screenshot viewer (item 3) — light, framed, scrollable; Download + Open in new
//    tab. Returns an element so per-step / batch can embed it; the main single-shot
//    path drops it into #result-steps. `src` is a data: URL or object URL. ──
function shotViewerEl(src, filename){
  const wrap=document.createElement('div');
  const view=document.createElement('div'); view.className='shot-viewer';
  const img=document.createElement('img'); img.src=src; img.alt='screenshot'; view.appendChild(img);
  const bar=document.createElement('div'); bar.className='shot-bar';
  const dl=document.createElement('a'); dl.textContent='Download'; dl.href=src; dl.download=filename||'screenshot.png';
  const open=document.createElement('a'); open.textContent='Open in new tab'; open.style.cursor='pointer';
  open.onclick=()=>{ const w=window.open(); if(w){ w.document.write('<img src="'+src+'" style="max-width:100%">'); w.document.title=filename||'screenshot'; } };
  bar.appendChild(dl); bar.appendChild(open); wrap.appendChild(view); wrap.appendChild(bar);
  return wrap;
}
function showShot(src, filename){                                                   // single-shot: clear placeholder, render the viewer in the steps area
  const steps=document.getElementById('result-steps'); steps.appendChild(shotViewerEl(src, filename));
  document.getElementById('placeholder').style.display='none';
}
function renderSingle(data, format){
  showMetaLine(`<strong>${format.toUpperCase()}</strong> <span>${escHtml(data.duration_ms??'?')}ms</span> <span style="font-family:monospace;font-size:.7rem;cursor:pointer" title="click to copy" onclick="copyText('${escHtml(data.trace_id||'')}');flash('trace id copied')">${escHtml(data.trace_id||'')}</span>`);
  if(format==='png' && data.screenshot_b64){ showShot('data:image/png;base64,'+data.screenshot_b64, (data.trace_id||'screenshot')+'.png'); }
  else if(data.html!==undefined && data.html!==null){ const pre=document.getElementById('result-html'); pre.textContent=data.html; pre.style.display='block'; }
}
function renderBatch(data, items){
  const shots = Array.isArray(data.screenshots) ? data.screenshots : [];
  showMetaLine(`<strong>${shots.length} result${shots.length!==1?'s':''}</strong> <span>${escHtml(data.duration_ms??'?')}ms</span>`);
  const grid=document.getElementById('batch-grid'); grid.innerHTML='';
  shots.forEach((s,i)=>{ const url=(items[i]||{}).url||`#${i+1}`; const u=escHtml(url);
    const t=document.createElement('div'); t.className='batch-thumb';
    if(s.screenshot_b64){                                                            // item 3: framed viewer with Download + Open per batch item
      const label=document.createElement('div'); label.className='thumb-label'; label.title=url; label.textContent=`${i+1}. ${url}`;
      t.appendChild(shotViewerEl('data:image/png;base64,'+s.screenshot_b64, `batch-${i+1}.png`)); t.appendChild(label);
    }
    else if(s.html) t.innerHTML=`<pre class="out" style="max-height:160px">${escHtml(s.html.slice(0,400))}…</pre><div class="thumb-label" title="${u}">${i+1}. ${u} (HTML)</div>`;
    else t.innerHTML=`<div class="thumb-label" style="color:var(--warn)">No result for ${u}</div>`;
    grid.appendChild(t); });
}
function statusPill(st){ return `<span class="pill ${escHtml(st||'')}">${escHtml(st||'?')}</span>`; }
function renderSequence(data){
  showMetaLine(`${statusPill(data.status)} <span>${escHtml(data.steps_passed??'?')}/${escHtml(data.steps_total??'?')} passed</span> <span>${escHtml(data.total_duration_ms??'?')}ms</span> <span style="font-family:monospace;font-size:.7rem">${escHtml(data.trace_id||'')}</span>`);
  renderStepResults(data.step_results||[]);
}
function renderInspect(data){
  showMetaLine(`${statusPill(data.status)} <span>${escHtml(data.total_duration_ms??'?')}ms</span> <span style="font-family:monospace;font-size:.7rem">${escHtml(data.trace_id||'')}</span>`);
  const wrap=document.getElementById('result-steps');
  const probes=data.probe_results||{};
  Object.keys(probes).forEach(name=>wrap.appendChild(stepResultEl(probes[name], name)));
  if(data.diagnostics){ const d=document.createElement('details'); d.innerHTML=`<summary>diagnostics</summary><pre class="out">${escHtml(JSON.stringify(data.diagnostics,null,2))}</pre>`; wrap.appendChild(d); }
}
function renderStepResults(steps){ const wrap=document.getElementById('result-steps'); steps.forEach((s,i)=>wrap.appendChild(stepResultEl(s, `${i+1}. ${s.action||''}`))); }
function stepResultEl(s, label){
  const div=document.createElement('div'); div.className='step-result';
  let body='';
  if(s.url!==undefined&&s.url!==null) body+=`<div>url: ${escHtml(s.url)}</div>`;
  if(s.text!==undefined&&s.text!==null) body+=`<pre class="out">${escHtml(String(s.text).slice(0,2000))}</pre>`;
  if(s.html!==undefined&&s.html!==null) body+=`<pre class="out">${escHtml(String(s.html).slice(0,2000))}</pre>`;
  if(s.content!==undefined&&s.content!==null) body+=`<pre class="out">${escHtml(String(s.content).slice(0,2000))}</pre>`;
  if(s.return_value!==undefined&&s.return_value!==null) body+=`<div>return_value: ${escHtml(JSON.stringify(s.return_value))}</div>`;
  if(s.dom_tree) body+=`<details><summary>dom_tree</summary><pre class="out">${escHtml(JSON.stringify(s.dom_tree,null,2))}</pre></details>`;
  if(s.accessibility_tree) body+=`<details><summary>accessibility_tree</summary><pre class="out">${escHtml(JSON.stringify(s.accessibility_tree,null,2))}</pre></details>`;
  if(s.console_log) body+=`<details><summary>console_log</summary><pre class="out">${escHtml(JSON.stringify(s.console_log,null,2))}</pre></details>`;
  if(s.network_failures) body+=`<details><summary>network_failures</summary><pre class="out">${escHtml(JSON.stringify(s.network_failures,null,2))}</pre></details>`;
  const shots=[];                                                                    // item 3: per-step screenshots get the framed viewer (Download / Open), appended after the text body
  (s.artefacts||[]).forEach((a,ai)=>{ if(a.inline_b64 && a.artefact_type==='SCREENSHOT') shots.push({src:'data:image/png;base64,'+a.inline_b64, name:`step-${escHtml(label).replace(/[^a-z0-9]+/gi,'-')||ai}.png`});
    else body+=`<div>artefact: ${escHtml(a.artefact_type||'?')} (${escHtml(a.sink||'?')})</div>`; });
  if(s.error_message) body+=`<div style="color:var(--danger)">${escHtml(s.error_message)}</div>`;
  div.innerHTML=`<div class="srh">${statusPill(s.status)}<span>${escHtml(label)}</span><span style="color:var(--muted)">${escHtml(s.duration_ms??'')}ms</span></div>${body}`;
  shots.forEach(sh=>div.appendChild(shotViewerEl(sh.src, sh.name)));
  return div;
}

// ════════════════════════════════════════════════════════════════════════════
//  Service tab
// ════════════════════════════════════════════════════════════════════════════
async function svcLoad(path){ switchTab('service'); const r=await apiGet(path); let d; try{ d=await r.json(); }catch{ d=await r.text(); } renderJson(d); }
async function svcMetrics(){ switchTab('service'); const r=await apiGet('/metrics'); const t=await r.text(); const pre=document.getElementById('result-html'); pre.textContent=t; pre.style.display='block'; document.getElementById('placeholder').style.display='none'; }
function renderCapsTable(){
  const wrap=document.getElementById('svc-caps'); if(!CAPABILITIES){ wrap.innerHTML='<div class="hint" style="color:var(--muted);background:var(--surface2);border-color:var(--border)">capabilities not loaded yet</div>'; return; }
  const rows=Object.entries(CAPABILITIES).map(([k,v])=>`<tr><td>${escHtml(k)}</td><td>${escHtml(Array.isArray(v)?v.join(', '):JSON.stringify(v))}</td></tr>`).join('');
  wrap.innerHTML=`<table class="cap-table">${rows}</table>`;
}

// ════════════════════════════════════════════════════════════════════════════
//  Docs tab (P4) — generated from VERBS + live CAPABILITIES (can't drift, D2/D4)
// ════════════════════════════════════════════════════════════════════════════
function renderDocs(){
  const c=document.getElementById('docs-content');
  let html='<div class="section-title">Deployment capabilities (live /health/capabilities)</div>';
  if(CAPABILITIES){ html+=`<table class="cap-table">${Object.entries(CAPABILITIES).map(([k,v])=>`<tr><td>${escHtml(k)}</td><td>${escHtml(Array.isArray(v)?v.join(', '):JSON.stringify(v))}</td></tr>`).join('')}</table>`; }
  else html+='<div class="hint">capabilities not loaded</div>';
  html+='<div class="section-title" style="margin-top:10px">Step verbs ('+VERB_LIST.length+') — POST /sequence/execute</div>';
  VERB_LIST.forEach(v=>{
    const fields=VERBS[v].filter(f=>f.n).map(f=>{ const meta=[f.req?'required':null,f.enum?ENUMS[f.enum].join('|'):null,f.def!==undefined?`default ${f.def}`:null,f.hint?'⚠ '+f.hint:null].filter(Boolean).join('; ');
      return `<div><code>${escHtml(f.n)}</code>${meta?' — '+escHtml(meta):''}</div>`; }).join('') || '<div><em>(no fields)</em></div>';
    html+=`<details class="docs-verb"><summary>${escHtml(v)}</summary><div class="dv-body">${fields}</div></details>`;
  });
  html+='<div class="section-title" style="margin-top:10px">Endpoint families</div>';
  html+='<div class="dv-body" style="color:var(--muted);font-size:.74rem">POST /screenshot · /screenshot/batch · /sequence/execute · /inspect · /session/open|act|probe|close · /browser/navigate|click|fill|get-content|get-url|screenshot · GET /health/info|status|capabilities · /metrics</div>';
  c.innerHTML=html;
}

// ════════════════════════════════════════════════════════════════════════════
//  Workflow import/export (P3) — portable JSON = /sequence/execute body + envelope
// ════════════════════════════════════════════════════════════════════════════
const WF_LS='sg_playwright_workflows';
function currentWorkflow(){
  const {path,body}=currentRequest();
  return { sg_playwright_workflow:1, name:'workflow-'+activeTab, tab:activeTab, endpoint:path, request:body };
}
function wfExportFile(){
  const wf=currentWorkflow(); const blob=new Blob([JSON.stringify(wf,null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=(wf.name||'workflow')+'.json'; a.click();
}
function wfImportFile(ev){ const f=ev.target.files[0]; if(!f)return; const rd=new FileReader();
  rd.onload=()=>{ try{ importWorkflow(JSON.parse(rd.result)); }catch(e){ alert('Invalid workflow JSON: '+e.message); } }; rd.readAsText(f); ev.target.value=''; }
function wfSaveLocal(){ const wf=currentWorkflow(); const name=prompt('Save workflow as:', wf.name); if(!name)return; wf.name=name;
  const store=JSON.parse(localStorage.getItem(WF_LS)||'{}'); store[name]=wf; localStorage.setItem(WF_LS,JSON.stringify(store)); flash('saved: '+name); }
function wfLoadLocal(){ const store=JSON.parse(localStorage.getItem(WF_LS)||'{}'); const names=Object.keys(store);
  if(!names.length){ alert('No saved workflows'); return; } const name=prompt('Load which?\n'+names.join('\n'), names[0]); if(!name||!store[name])return; importWorkflow(store[name]); }
function exportWorkflow(){ return currentWorkflow(); }
function importWorkflow(wf){
  if(!wf || !wf.request){ alert('Not a workflow file'); return; }
  const tab=wf.tab||tabForEndpoint(wf.endpoint); if(tab) switchTab(tab);
  loadBodyIntoBuilder(tab, wf.endpoint, wf.request);
}
function tabForEndpoint(ep){
  if(!ep) return 'sequence';
  if(ep.startsWith('/screenshot')) return 'screenshot';
  if(ep.startsWith('/sequence')) return 'sequence';
  if(ep.startsWith('/inspect')) return 'inspect';
  if(ep.startsWith('/browser')) return 'browser';
  if(ep.startsWith('/session')) return 'session';
  return 'sequence';
}
function loadBodyIntoBuilder(tab, endpoint, body){
  if(tab==='sequence' || (endpoint||'').startsWith('/sequence')){
    document.getElementById('seq-steps').innerHTML=''; for(const k in seqData)delete seqData[k];
    (body.steps||[]).forEach(st=>loadSeqStep(st));
    document.getElementById('seq-shot-enabled').checked = !!(body.capture_config&&body.capture_config.screenshot&&body.capture_config.screenshot.enabled);
    document.getElementById('seq-pdf-enabled').checked  = !!(body.capture_config&&body.capture_config.pdf&&body.capture_config.pdf.enabled);
  } else if(tab==='inspect' || (endpoint||'').startsWith('/inspect')){
    document.getElementById('ins-url').value = body.navigate ? (body.navigate.url||'') : '';
    document.getElementById('ins-settle').checked = !!(body.settle&&body.settle.length);
    document.getElementById('ins-diag').checked = body.diagnostics_on_fail!==false;
    document.getElementById('ins-probes').innerHTML=''; for(const k in insData)delete insData[k];
    Object.entries(body.probes||{}).forEach(([name,probe])=>loadInsProbe(name,probe));
  } else if(tab==='screenshot' || (endpoint||'').startsWith('/screenshot')){
    if(body.url!==undefined){ setSsMode('single'); document.getElementById('ss-url').value=body.url||''; setFmt(body.format||'png');
      document.getElementById('ss-js').value=body.javascript||''; document.getElementById('ss-click').value=body.click||''; document.getElementById('ss-full').checked=!!body.full_page; }
    else { setSsMode('batch'); setBatchMode(body.steps?'steps':'items');
      document.getElementById('ss-cards').innerHTML=''; for(const k in cardData)delete cardData[k];
      (body.items||body.steps||[]).forEach(it=>{ addCard(it.url||''); }); }
  }
}
function loadSeqStep(st){
  if(!st||!st.action||!VERBS[st.action]) return;
  seqAddStep(st.action);
  const el=document.querySelector('#seq-steps .step-card:last-child'); const id=el.dataset.id;
  VERBS[st.action].forEach(f=>{ if(!f.n||st[f.n]===undefined)return;
    let v=st[f.n]; if(f.type==='list'&&Array.isArray(v))v=v.join(',');
    if(f.type==='viewport'){ seqData[id].viewport=v; return; }
    seqData[id][f.n]=v;
    const inp=document.getElementById(`seq-${id}-${f.n}`); if(inp){ if(inp.type==='checkbox')inp.checked=!!v; else inp.value=v; } });
}
function loadInsProbe(name,probe){
  if(!probe||!probe.action||!VERBS[probe.action])return;
  insAddProbe(probe.action);
  const el=document.querySelector('#ins-probes .step-card:last-child'); const id=el.dataset.id;
  insNames[id]=name; const nameInp=el.querySelector('input[type=text]'); if(nameInp)nameInp.value=name;
  VERBS[probe.action].forEach(f=>{ if(!f.n||probe[f.n]===undefined)return; let v=probe[f.n];
    insData[id][f.n]=v; const inp=document.getElementById(`ins-${id}-${f.n}`); if(inp){ if(inp.type==='checkbox')inp.checked=!!v; else inp.value=v; } });
}

// ════════════════════════════════════════════════════════════════════════════
//  Example gallery (W1–W9) — REAL verbs/fields from the capability map (brief 02)
// ════════════════════════════════════════════════════════════════════════════
// S-series: self-contained examples (Decision #5) targeting the service's own
// /test-pages/* fixtures. URLs are resolved at LOAD time off
// window.location.origin + window.API_BASE so they run against THIS deployment with
// no external egress. They are the headline of the gallery; W1-W9 follow as
// public-site recipes. tpUrl() composes the absolute fixture URL.
function tpUrl(name){ return window.location.origin + window.API_BASE + '/test-pages/' + name; }
const GALLERY = [
  { id:'S1', title:'Screenshot a fixture page', tab:'screenshot', endpoint:'/screenshot',
    request:{ url:tpUrl('simple'), format:'png' } },
  { id:'S2', title:'Inspect DOM of a fixture page', tab:'inspect', endpoint:'/inspect',
    request:{ navigate:{url:tpUrl('simple')}, settle:[], diagnostics_on_fail:true,
      probes:{ current_url:{action:'get_url'}, page_text:{action:'get_text'},
        dom:{action:'get_dom_tree',max_depth:6,include_invisible:false} } } },
  { id:'S3', title:'Fill + submit a form (per-step shot)', tab:'sequence', endpoint:'/sequence/execute',
    request:{ capture_config:{screenshot:{enabled:true,sink:'inline'}}, steps:[
      {action:'navigate',url:tpUrl('form'),wait_until:'domcontentloaded'},
      {action:'fill',selector:'#username',value:'demo'},
      {action:'fill',selector:'#password',value:'hunter2'},
      {action:'click',selector:'#submit'},
      {action:'wait_for',selector:'#welcome'},
      {action:'screenshot',full_page:true} ] } },
  { id:'S4', title:'Wait for a deferred selector', tab:'sequence', endpoint:'/sequence/execute',
    request:{ steps:[
      {action:'navigate',url:tpUrl('dynamic'),wait_until:'domcontentloaded'},
      {action:'wait_for',selector:'#ready'},
      {action:'get_text',selector:'#ready'} ] } },
  { id:'S5', title:'Navigate / scroll / selector capture', tab:'sequence', endpoint:'/sequence/execute',
    request:{ capture_config:{screenshot:{enabled:true,sink:'inline'}}, steps:[
      {action:'navigate',url:tpUrl('links'),wait_until:'domcontentloaded'},
      {action:'scroll',y:2000},
      {action:'wait_for',selector:'#bottom'},
      {action:'screenshot',selector:'#gamma'} ] } },
  { id:'W1', title:'Form fill + wait + per-step shots', tab:'sequence', endpoint:'/sequence/execute',
    request:{ capture_config:{screenshot:{enabled:true,sink:'inline'}}, steps:[
      {action:'navigate',url:'https://example.com/login',wait_until:'domcontentloaded'},
      {action:'fill',selector:'#email',value:'demo@example.com'},
      {action:'fill',selector:'#password',value:'hunter2'},
      {action:'screenshot',full_page:false},
      {action:'click',selector:'button[type=submit]'},
      {action:'wait_for',text:'Welcome',timeout_ms:10000},
      {action:'screenshot',full_page:true} ] } },
  { id:'W2', title:'Login then navigate then extract', tab:'sequence', endpoint:'/sequence/execute',
    request:{ steps:[
      {action:'navigate',url:'https://app.example.com/login'},
      {action:'fill',selector:'#user',value:'demo'},
      {action:'fill',selector:'#pass',value:'demo'},
      {action:'click',selector:'#sign-in'},
      {action:'wait_for',url_pattern:'https://app.example.com/dashboard',timeout_ms:15000},
      {action:'navigate',url:'https://app.example.com/reports/42'},
      {action:'wait_for',selector:'[data-ready=true]'},
      {action:'get_url'},
      {action:'get_text',selector:'main'} ] } },
  { id:'W3', title:'Scrape DOM + a11y (via /inspect)', tab:'inspect', endpoint:'/inspect',
    request:{ navigate:{url:'https://sgraph.ai'}, settle:[{action:'wait_for',state:'networkidle'}], diagnostics_on_fail:true,
      probes:{ current_url:{action:'get_url'}, page_text:{action:'get_text'},
        dom:{action:'get_dom_tree',max_depth:6,include_invisible:false}, a11y:{action:'get_a11y_tree',interesting_only:true},
        html_head:{action:'get_html',selector:'head'} } } },
  { id:'W4', title:'Render a PDF', tab:'sequence', endpoint:'/sequence/execute',
    request:{ capture_config:{pdf:{enabled:true,sink:'inline'}}, steps:[
      {action:'navigate',url:'https://sgraph.ai/about',wait_until:'load'},
      {action:'wait_for',state:'networkidle'},
      {action:'get_pdf',format:'A4',landscape:false,print_background:true} ] } },
  { id:'W5', title:'Console + network on a failing page', tab:'inspect', endpoint:'/inspect',
    request:{ navigate:{url:'https://example.com/broken'}, settle:[], diagnostics_on_fail:true,
      probes:{ console:{action:'get_console_tail',lines:200}, failures:{action:'get_network_failures'}, shot:{action:'screenshot',full_page:true} } } },
  { id:'W6', title:'Viewport/frame/selector capture', tab:'sequence', endpoint:'/sequence/execute',
    request:{ capture_config:{screenshot:{enabled:true,sink:'inline'}}, steps:[
      {action:'navigate',url:'https://example.com'},
      {action:'set_viewport',viewport:{width:1440,height:900}},
      {action:'screenshot',full_page:true},
      {action:'screenshot',selector:'header.site-header'},
      {action:'screenshot',frame_selector:'iframe#embed',viewport:{width:800,height:600}} ] } },
  { id:'W7', title:'Hover/select/press/scroll/evaluate', tab:'sequence', endpoint:'/sequence/execute',
    request:{ capture_config:{screenshot:{enabled:true,sink:'inline'}}, steps:[
      {action:'navigate',url:'https://example.com/catalog'},
      {action:'hover',selector:'nav .menu'},
      {action:'select',selector:'#sort',values:['price-asc']},
      {action:'press',selector:'#search',key:'Enter'},
      {action:'scroll',y:2000},
      {action:'wait_for',selector:'.results .item'},
      {action:'evaluate',expression:"document.querySelectorAll('.item').length",return_type:'number'},
      {action:'screenshot',full_page:true} ] } },
  { id:'W8', title:'Batch screenshots (items)', tab:'screenshot', endpoint:'/screenshot/batch',
    request:{ items:[
      {url:'https://sgraph.ai',full_page:true},
      {url:'https://example.com',format:'png'},
      {url:'https://example.org',javascript:"document.body.style.zoom='80%'"} ] } },
  { id:'W9', title:'Stateful session (open/act/probe/close)', tab:'session', endpoint:'/sequence/execute',
    request:{ steps:[
      {action:'navigate',url:'https://app.example.com'},
      {action:'wait_for',text:'Dashboard'} ] } },
];
function renderGallery(){
  const g=document.getElementById('gallery');
  g.innerHTML = GALLERY.map(w=>`<button onclick="loadExample('${w.id}')"><span class="gw">${escHtml(w.id)}</span> ${escHtml(w.title)}<span class="gd">${escHtml(w.endpoint)}</span></button>`).join('');
}
function loadExample(id){
  const w=GALLERY.find(x=>x.id===id); if(!w)return;
  switchTab(w.tab); loadBodyIntoBuilder(w.tab, w.endpoint, w.request); flash('loaded '+id);
}

// ════════════════════════════════════════════════════════════════════════════
//  Bootstrap (auth-aware) — health badge + info + capabilities; gates UI (P2)
// ════════════════════════════════════════════════════════════════════════════
let CAPABILITIES = null, SERVICE_INFO = null;
function showServiceInfo(info){
  const el=document.getElementById('svc-info'); if(!el||!info)return;
  el.textContent=[info.service_version, info.chromium_version&&('chromium '+info.chromium_version), info.deployment_target].filter(Boolean).join(' · ');
}
function applyCapabilities(){
  if(!CAPABILITIES) return;
  // Session disabled when not persistent
  const persistent = CAPABILITIES.supports_persistent !== false;
  const sessBtn=document.querySelector('.tab-rail button[data-tab="session"]');
  if(sessBtn){ sessBtn.disabled=!persistent; if(!persistent) sessBtn.innerHTML='Session<span class="cap-off">unavailable</span>'; }
  const sessDisabled=document.getElementById('sess-disabled'); if(sessDisabled) sessDisabled.style.display = persistent?'none':'block';
  // Video verbs hidden when unsupported
  const sel=document.getElementById('seq-add-verb');
  if(sel){ const allowed = VERB_LIST.filter(v=>{ if((v==='video_start'||v==='video_stop')&&CAPABILITIES.supports_video===false)return false; return true; });
    sel.innerHTML = allowed.map(v=>`<option>${v}</option>`).join(''); }
  // Sink picker limited to supported_sinks; default inline
  const sinkSel=document.getElementById('seq-sink');
  if(sinkSel){ const sinks=(Array.isArray(CAPABILITIES.supported_sinks)&&CAPABILITIES.supported_sinks.length)?CAPABILITIES.supported_sinks:['inline'];
    sinkSel.innerHTML = sinks.map(s=>`<option ${/inline/i.test(s)?'selected':''}>${escHtml(s)}</option>`).join(''); }
}
async function bootstrap(){
  const badge=document.getElementById('health-badge');
  try{ const r=await apiGet('/health/status'); const d=await r.json(); const ok=d.healthy===true;
    badge.textContent=ok?'● healthy':'● degraded'; badge.className='badge '+(ok?'ok':'err'); }
  catch{ badge.textContent='● unreachable'; badge.className='badge err'; }
  try{ const r=await apiGet('/health/info');         if(r.ok){ SERVICE_INFO=await r.json(); showServiceInfo(SERVICE_INFO); } }catch{}
  try{ const r=await apiGet('/health/capabilities'); if(r.ok){ CAPABILITIES=await r.json(); } }catch{}
  applyCapabilities();
}

// docs/skills/cookie links — all prefix-aware (compose off window.API_BASE; never absolute-rooted)
(function(){
  const dl=document.getElementById('docs-link');   if(dl)dl.href=window.API_BASE+'/docs';
  const sl=document.getElementById('skills-link'); if(sl)sl.href=window.API_BASE+'/admin/skills/human';
  const cl=document.getElementById('cookie-link'); if(cl)cl.href=window.API_BASE+'/auth/set-cookie-form';
})();

// initial verb dropdowns (replaced by applyCapabilities once caps arrive)
document.getElementById('seq-add-verb').innerHTML = VERB_LIST.map(v=>`<option>${v}</option>`).join('');
document.getElementById('ins-add-verb').innerHTML = PROBE_VERBS.map(v=>`<option>${v}</option>`).join('');
document.getElementById('seq-sink').innerHTML = '<option selected>inline</option>';
brRenderFields();
renderGallery();
addCard('https://sgraph.ai'); addCard('');
bootstrap();
let _bootT; keyEl.addEventListener('input', ()=>{ clearTimeout(_bootT); _bootT=setTimeout(bootstrap,400); });

// Ctrl/Cmd+Enter executes the active tab (but not when the console input is focused —
// that has its own handler so the two REPLs don't collide).
document.addEventListener('keydown', e=>{ if(!(e.ctrlKey||e.metaKey)||e.key!=='Enter')return;
  if(document.activeElement && document.activeElement.id==='console-input')return;
  ({screenshot:execScreenshot,sequence:execSequence,inspect:execInspect,browser:execBrowser,debug:execDebug}[activeTab]||(()=>{}))(); });

// ════════════════════════════════════════════════════════════════════════════
//  Resizable work area (item 2) — the three light panes live in a CSS grid
//  (builder | result over a full-width console). Two drag handles resize the
//  column split (--lc/--rc) and the console height (--cr); sizes persist to
//  localStorage. This is pure in-house DOM — no external web component and no
//  reparenting of the panes — so the console always renders and never depends on
//  a CDN. (We dropped the sg-layout web component here: its panel API instantiates
//  components via a `tag`, and does not project our existing plain-div panes.)
// ════════════════════════════════════════════════════════════════════════════
const SG_SIZES_LS = 'sg-playwright:console:sizes:v1';
function setupResizers(){
  const area=document.getElementById('work-area'); if(!area) return;
  try{ const s=JSON.parse(localStorage.getItem(SG_SIZES_LS)||'null'); if(s){
    if(s.lc) area.style.setProperty('--lc', s.lc); if(s.rc) area.style.setProperty('--rc', s.rc);
    if(s.cr) area.style.setProperty('--cr', s.cr); } }catch(e){}
  const save=()=>{ try{ localStorage.setItem(SG_SIZES_LS, JSON.stringify({
    lc:area.style.getPropertyValue('--lc'), rc:area.style.getPropertyValue('--rc'), cr:area.style.getPropertyValue('--cr') })); }catch(e){} };
  const dragCol=e=>{ const r=area.getBoundingClientRect(); let t=(e.clientX-r.left)/r.width;
    t=Math.min(0.8,Math.max(0.2,t)); area.style.setProperty('--lc', t.toFixed(3)+'fr'); area.style.setProperty('--rc', (1-t).toFixed(3)+'fr'); };
  const dragRow=e=>{ const r=area.getBoundingClientRect(); let h=r.bottom-e.clientY;
    h=Math.min(r.height*0.7,Math.max(80,h)); area.style.setProperty('--cr', Math.round(h)+'px'); };
  const start=move=>e=>{ e.preventDefault();
    const mv=ev=>move(ev), up=()=>{ document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up); save(); };
    document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up); };
  const v=document.getElementById('vsplit'), h=document.getElementById('hsplit');
  if(v) v.addEventListener('pointerdown', start(dragCol));
  if(h) h.addEventListener('pointerdown', start(dragRow));
}
setupResizers();

// ════════════════════════════════════════════════════════════════════════════
//  Bottom __tool console (item 6) — live REPL over window.__tool, in the OPERATOR's
//  browser (NOT the server-side evaluate allowlist). Evals entered JS in an async
//  scope with __tool in scope; renders the return value as escaped pretty JSON; if
//  the value carries an imageSrc / base64 PNG it is shown via the item-3 viewer.
//  ALL output escaped via escHtml. Token never echoed.
// ════════════════════════════════════════════════════════════════════════════
function consoleQuick(src){ document.getElementById('console-input').value=src; consoleRun(); }
function _consoleImageSrc(v){                                                       // detect a renderable image in a returned value
  if(!v||typeof v!=='object') return null;
  if(typeof v.imageSrc==='string') return v.imageSrc;
  if(typeof v.screenshot_b64==='string') return 'data:image/png;base64,'+v.screenshot_b64;
  if(Array.isArray(v.screenshots)&&v.screenshots[0]&&typeof v.screenshots[0].screenshot_b64==='string') return 'data:image/png;base64,'+v.screenshots[0].screenshot_b64;
  return null;
}
async function consoleRun(){
  const src=document.getElementById('console-input').value; const out=document.getElementById('console-out');
  out.innerHTML='<div class="sr"><span class="spin"></span><span>running…</span></div>';
  const __tool=window.__tool;                                                       // bring __tool into the eval scope explicitly
  try{
    const fn=new Function('__tool', '"use strict"; return (async()=>{ return ('+src+'); })();');
    const result=await fn(__tool);
    const img=_consoleImageSrc(result);
    out.innerHTML='';
    if(img){ out.appendChild(shotViewerEl(img, 'console.png')); }
    const pre=document.createElement('pre'); pre.className='out';
    let txt; try{ txt=JSON.stringify(result,null,2); }catch(e){ txt=String(result); }
    pre.innerHTML=escHtml(txt===undefined?'undefined':txt); out.appendChild(pre);
  }catch(e){ out.innerHTML='<pre class="out" style="color:var(--danger)">'+escHtml(String(e&&e.message||e))+'</pre>'; }
}
document.getElementById('console-input').addEventListener('keydown', e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){ e.preventDefault(); consoleRun(); }
});

// ════════════════════════════════════════════════════════════════════════════
//  Agentic window.__tool (P5) — agentic-js-api house pattern (brief 05 §3).
//  sg-tool-api component was NOT reachable on the CDN at build time (404), so this
//  is a CONTRACT-COMPATIBLE in-page registration of the documented sg-tool-api
//  surface (window.__tool + meta.* + SGA_TOOL + __tool_registry). Byte-compatible
//  with the house pattern so an agent that knows sg-tool-api needs no extra knowledge.
//  SECURITY: no getter or log ever exposes the token (setAuth writes, nothing reads back).
// ════════════════════════════════════════════════════════════════════════════
window.SGA_TOOL = Object.freeze({ RUN_STARTED:'tool:run:started', RUN_COMPLETE:'tool:run:complete' });
function _httpJson(method, path, body){ return request(method, path, body).then(r=>r.data); }
const TOOL_API_VERSION = 'v0.2.64';
function _apiSkill(){
  let md = `# sg-playwright window.__tool API (${TOOL_API_VERSION})\n\nAuth: setAuth({token, authMode:'apiKey'|'proxy'}). Header: ${authHeaderName()}.\n\n## Methods\n`;
  md += '- screenshot({url, format, full_page, javascript, click}) → POST /screenshot\n';
  md += '- batch({items}) → POST /screenshot/batch\n';
  md += '- sequence({steps, screenshot_per_step}) → POST /sequence/execute\n';
  md += '- inspect(body) → POST /inspect\n';
  md += '- browser(verb, body) → POST /browser/{verb}\n';
  md += '- session.open(body) / act(id,body) / probe(id,body) / close(id)\n';
  md += '\n## Step verbs (POST /sequence/execute)\n';
  VERB_LIST.forEach(v=>{ const fs=VERBS[v].filter(f=>f.n).map(f=>f.n+(f.req?'*':'')).join(', '); md+=`- ${v}(${fs})\n`; });
  if(CAPABILITIES){ md+='\n## Deployment capabilities (live)\n'; Object.entries(CAPABILITIES).forEach(([k,v])=>md+=`- ${k}: ${Array.isArray(v)?v.join('|'):JSON.stringify(v)}\n`); }
  return md;
}
window.__tool = {
  async screenshot({url, format, full_page, javascript, click}={}){ const b={url}; if(format)b.format=format; if(full_page)b.full_page=true; if(javascript)b.javascript=javascript; if(click)b.click=click; return _httpJson('POST','/screenshot',b); },
  async batch({items}={}){ return _httpJson('POST','/screenshot/batch',{items}); },
  async sequence({steps, screenshot_per_step, capture_config}={}){ const b={steps}; if(screenshot_per_step!==undefined)b.screenshot_per_step=screenshot_per_step; if(capture_config)b.capture_config=capture_config; return _httpJson('POST','/sequence/execute',b); },
  async inspect(body){ return _httpJson('POST','/inspect',body); },
  async browser(verb, body){ return _httpJson('POST','/browser/'+verb, body); },
  session: {
    async open(body){ return _httpJson('POST','/session/open', body||{browser_config:{}}); },
    async act(id, body){ return _httpJson('POST',`/session/${encodeURIComponent(id)}/act`, body); },
    async probe(id, body){ return _httpJson('POST',`/session/${encodeURIComponent(id)}/probe`, body); },
    async close(id){ return _httpJson('POST',`/session/${encodeURIComponent(id)}/close`); },
  },
  async run(workflowOrBody){
    const wf = workflowOrBody && workflowOrBody.request ? workflowOrBody : null;
    const ep = wf ? wf.endpoint : '/sequence/execute';
    const body = wf ? wf.request : workflowOrBody;
    window.dispatchEvent(new CustomEvent(window.SGA_TOOL.RUN_STARTED,{detail:{endpoint:ep}}));
    const data = await _httpJson('POST', ep, body);
    window.dispatchEvent(new CustomEvent(window.SGA_TOOL.RUN_COMPLETE,{detail:{endpoint:ep}}));
    return data;
  },
  loadExample(id){ loadExample(id); },
  exportWorkflow(){ return exportWorkflow(); },
  importWorkflow(obj){ importWorkflow(obj); },
  setAuth(opts){ setAuth(opts); },                                                  // writes token; no getter reads it back
  getState(){ return { activeTab, authMode, sessionId, capabilities: CAPABILITIES, serviceInfo: SERVICE_INFO }; },
  getRuns(n){ return runLog.slice(-(n||20)); },                                      // no token, no bodies
  getActiveTab(){ return activeTab; },
  meta: {
    getMethods(){ return ['screenshot','batch','sequence','inspect','browser','session.open','session.act','session.probe','session.close','run','loadExample','exportWorkflow','importWorkflow','setAuth','getState','getRuns','getActiveTab']; },
    getVersion(){ return { api: TOOL_API_VERSION, service: (SERVICE_INFO&&SERVICE_INFO.service_version)||null }; },
    getManifest(){ return CAPABILITIES; },                                          // cached /health/capabilities
    async getSkills(){ return {
      human:   '# SG Playwright Console\n\nA capability-driven console for the sg-playwright service. Pick a tab (Screenshot, Sequence, Inspect, Session, Browser, Debug, Service), build a request, set your auth key, and Execute. Load an example (W1–W9) to start. Every request is exportable as JSON or curl.',
      browser: '# Driving sg-playwright via Playwright\n\n```js\nawait page.evaluate(() => window.__tool.setAuth({token:KEY, authMode:"apiKey"}))\nconst r = await page.evaluate(() => window.__tool.sequence({steps:[{action:"navigate",url:"https://sgraph.ai"},{action:"get_url"}]}))\n```\nResults follow Schema__Sequence__Response: r.status, r.step_results[].',
      api:     _apiSkill(),
    }; },
    async health(){ return _httpJson('GET','/health/status'); },
    getLog(){ return runLog.slice(); },                                             // token NEVER present in runLog
  },
};
window.__tool_registry = { find(){ return window.__tool; }, findAll(){ return [window.__tool]; }, findById(){ return window.__tool; } };
</script>
</body>
</html>
'''


class Routes__Index(Fast_API__Routes):
    tag : str = 'index'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')    # Mount at root

    @route_path('/')
    def index(self, request: Request) -> HTMLResponse:
        api_base = Root_Path__Resolver().resolve(request)                            # Per-request: X-Forwarded-Prefix header (proxy) → SG_PLAYWRIGHT__ROOT_PATH env → '/pw' default. Single source of truth shared with the root_path middleware.
        return HTMLResponse(content=INDEX_HTML.replace('__API_BASE__', api_base))

    def setup_routes(self):
        self.add_route_get(self.index)
