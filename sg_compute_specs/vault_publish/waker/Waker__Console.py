# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Waker__Console
# Self-contained HTML+JS console for the /__waker__/cmd RPC endpoint.
# Lets an operator pick a command from a dropdown, type key=val args, hit
# Run, and see the JSON response right next to the command picker. No
# external assets — everything inlined so it works straight from the
# Lambda Function URL.
#
# Same gate as /__waker__/cmd: WAKER_CMD_ENABLED='1' on the function env.
# ═══════════════════════════════════════════════════════════════════════════════

CONSOLE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Vault Waker — Console</title>
<style>
  :root {
    --bg: #f7f7f8; --fg: #222; --muted: #888; --border: #e4e4e7;
    --accent: #2563eb; --danger: #b00020; --code-bg: #1e1e2e; --code-fg: #d4d4d8;
  }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
         background: var(--bg); color: var(--fg); margin: 0; padding: 0; }
  header { background: #fff; border-bottom: 1px solid var(--border);
           padding: .8rem 1.5rem; display: flex; align-items: baseline; gap: .8rem; }
  header h1 { margin: 0; font-size: 1.1rem; }
  header .badge { background: #dcfce7; color: #166534; font-size: .7rem;
                   padding: 2px 8px; border-radius: 10px; }
  header .links { margin-left: auto; font-size: .85rem; }
  header .links a { color: var(--accent); text-decoration: none; margin-left: 1rem; }
  main { max-width: 1100px; margin: 1.5rem auto; padding: 0 1.5rem;
         display: grid; grid-template-columns: 320px 1fr; gap: 1.5rem; }
  section { background: #fff; border: 1px solid var(--border); border-radius: 6px;
            padding: 1rem 1.2rem; }
  section h2 { margin: 0 0 .8rem; font-size: .9rem; color: #555;
               text-transform: uppercase; letter-spacing: .04em; }
  label { display: block; font-size: .8rem; color: var(--muted); margin: .6rem 0 .25rem; }
  select, input, button { font-family: inherit; font-size: .9rem;
                           border: 1px solid var(--border); border-radius: 4px;
                           padding: .4rem .6rem; box-sizing: border-box; }
  select, input { width: 100%; }
  button { background: var(--accent); color: #fff; border-color: var(--accent);
           cursor: pointer; padding: .5rem 1rem; margin-top: .8rem; }
  button:hover { background: #1d4ed8; }
  button:disabled { background: #94a3b8; border-color: #94a3b8; cursor: wait; }
  .arg-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: .4rem;
              margin-top: .3rem; align-items: center; }
  .arg-row button { background: transparent; color: var(--danger);
                     border-color: var(--border); margin-top: 0; padding: .35rem .6rem; }
  .arg-row button:hover { background: #fff0f0; }
  #add-arg { background: transparent; color: var(--accent); border-color: var(--border);
              padding: .3rem .7rem; margin-top: .4rem; font-size: .8rem; }
  .meta { font-size: .8rem; color: var(--muted); margin-top: .5rem; }
  .meta code { background: var(--bg); padding: 1px 5px; border-radius: 3px; }
  pre { background: var(--code-bg); color: var(--code-fg); padding: 1rem;
        border-radius: 4px; overflow-x: auto; font-size: .82rem;
        margin: 0; font-family: "SF Mono", "Menlo", monospace; }
  .status-line { font-size: .85rem; margin-bottom: .6rem; }
  .status-line .ok { color: #166534; font-weight: 600; }
  .status-line .err { color: var(--danger); font-weight: 600; }
  .desc { font-size: .82rem; color: var(--muted); margin-top: .4rem;
           padding: .5rem; background: var(--bg); border-radius: 4px;
           min-height: 2.2rem; }
  .desc.mutates { background: #fff0f0; color: #7f1d1d; }
  .desc.mutates::before { content: "MUTATES "; font-weight: 700; }
  .empty { color: var(--muted); font-style: italic; font-size: .85rem; }
  footer { text-align: center; font-size: .75rem; color: var(--muted);
           padding: 1.5rem 0 2rem; }
</style>
</head>
<body>
<header>
  <h1>Vault Waker — Console</h1>
  <span class="badge">dev-only</span>
  <div class="links">
    <a href="/__waker__/deploy">deploy info</a>
    <a href="/__waker__/health">health</a>
    <a href="/__waker__/docs">docs</a>
  </div>
</header>

<main>
  <section>
    <h2>Run a command</h2>
    <label for="cmd-select">Command</label>
    <select id="cmd-select"><option>Loading…</option></select>
    <div class="desc" id="cmd-desc">Loading commands…</div>

    <label>Arguments <span style="color: var(--muted); font-weight: normal;">(key=value)</span></label>
    <div id="args"></div>
    <button type="button" id="add-arg">+ add arg</button>

    <button type="button" id="run-btn">Run</button>
    <p class="meta">
      Channel gate: <code>WAKER_CMD_ENABLED</code> ·
      Mutations gate: <code>WAKER_CMD_MUTATIONS_ENABLED</code>
    </p>
  </section>

  <section>
    <h2>Response</h2>
    <div class="status-line" id="status-line"><span class="empty">No command run yet.</span></div>
    <pre id="response">{}</pre>
  </section>
</main>

<footer>Served by <code>/__waker__/console</code> on the vault-publish waker Lambda.</footer>

<script>
  const cmdSelect = document.getElementById('cmd-select');
  const cmdDesc   = document.getElementById('cmd-desc');
  const argsBox   = document.getElementById('args');
  const runBtn    = document.getElementById('run-btn');
  const respPre   = document.getElementById('response');
  const statusLn  = document.getElementById('status-line');
  let registry = [];

  function addArgRow(k, v) {
    const row = document.createElement('div');
    row.className = 'arg-row';
    row.innerHTML = '<input type="text" placeholder="key" value="' + (k||'') + '">'
                  + '<input type="text" placeholder="value" value="' + (v||'') + '">'
                  + '<button type="button" onclick="this.parentElement.remove()">x</button>';
    argsBox.appendChild(row);
  }
  document.getElementById('add-arg').onclick = function () { addArgRow(); };

  function refreshDesc() {
    const name = cmdSelect.value;
    const entry = registry.find(function (c) { return c.name === name; });
    if (!entry) { cmdDesc.textContent = ''; cmdDesc.className = 'desc'; return; }
    cmdDesc.textContent = entry.description || '(no description)';
    cmdDesc.className = entry.mutates ? 'desc mutates' : 'desc';
  }
  cmdSelect.onchange = refreshDesc;

  function buildQs() {
    const name = cmdSelect.value;
    const parts = ['name=' + encodeURIComponent(name)];
    argsBox.querySelectorAll('.arg-row').forEach(function (row) {
      const ins = row.querySelectorAll('input');
      const k = ins[0].value.trim(), v = ins[1].value;
      if (k) parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
    });
    return parts.join('&');
  }

  async function run() {
    runBtn.disabled = true; runBtn.textContent = 'Running…';
    statusLn.innerHTML = '<span class="empty">Calling /__waker__/cmd …</span>';
    const t0 = performance.now();
    try {
      const resp = await fetch('/__waker__/cmd?' + buildQs(), { headers: { 'Accept': 'application/json' } });
      const text = await resp.text();
      const ms   = Math.round(performance.now() - t0);
      let parsed;
      try { parsed = JSON.parse(text); } catch (e) { parsed = text; }
      respPre.textContent = (typeof parsed === 'string') ? parsed : JSON.stringify(parsed, null, 2);
      const ok = resp.ok && !(parsed && parsed.error);
      statusLn.innerHTML = '<span class="' + (ok ? 'ok' : 'err') + '">'
                          + (ok ? 'OK' : 'ERR') + '</span> — HTTP ' + resp.status + ' in ' + ms + 'ms';
    } catch (err) {
      respPre.textContent = String(err);
      statusLn.innerHTML = '<span class="err">network error</span>';
    } finally {
      runBtn.disabled = false; runBtn.textContent = 'Run';
    }
  }
  runBtn.onclick = run;

  fetch('/__waker__/cmd?name=help').then(function (r) { return r.json(); }).then(function (data) {
    registry = (data && data.result) || [];
    cmdSelect.innerHTML = '';
    registry.forEach(function (c) {
      const opt = document.createElement('option');
      opt.value = c.name; opt.textContent = c.name + (c.mutates ? '  [M]' : '');
      cmdSelect.appendChild(opt);
    });
    refreshDesc();
  }).catch(function (err) {
    cmdSelect.innerHTML = '<option>(failed to load)</option>';
    cmdDesc.textContent = 'Failed to load commands: ' + err;
  });
</script>
</body>
</html>
"""
