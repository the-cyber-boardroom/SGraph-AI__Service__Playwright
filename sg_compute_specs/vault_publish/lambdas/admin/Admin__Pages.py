# ═══════════════════════════════════════════════════════════════════════════════
# Admin — Admin__Pages
# Vanilla-HTML rendering of the admin UI pages. No framework dependency, no
# build step — strings only. The JS that runs on each page polls the JSON API
# (sibling Admin__API module) for live data.
#
# Three pages today (more in v0.1.16):
#   - login        : api-key form, sets cookie
#   - inventory    : list of all registered slugs + current state
#   - per_slug     : 7-step status (mirrors sg vp eval)
# ═══════════════════════════════════════════════════════════════════════════════

import html as html_lib
import json


_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
       max-width: 1080px; margin: 0 auto; padding: 1rem 2rem; color: #222; background: #fafafa; }
header { display: flex; justify-content: space-between; align-items: baseline;
         border-bottom: 2px solid #2e7d32; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
h1 { font-size: 1.4rem; margin: 0; color: #2e7d32; font-weight: 600; }
header nav a { color: #2e7d32; text-decoration: none; margin-left: 1rem; font-size: 0.9rem; }
header nav a:hover { text-decoration: underline; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); border-radius: 4px; overflow: hidden; }
th, td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #eee; text-align: left; }
th { background: #f5f5f5; font-weight: 600; color: #444; font-size: 0.82rem;
     text-transform: uppercase; letter-spacing: 0.04em; }
tr:hover { background: #fafafa; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
       margin-right: 0.4rem; vertical-align: middle; }
.dot.ok    { background: #2e7d32; }
.dot.warn  { background: #f9a825; }
.dot.err   { background: #c62828; }
.dot.idle  { background: #999; }
.mono { font-family: SFMono-Regular, Menlo, monospace; font-size: 0.85rem; }
code { background: #eee; padding: 1px 5px; border-radius: 3px; font-family: SFMono-Regular, Menlo, monospace; font-size: 0.85rem; }
.btn { font-family: inherit; font-size: 0.85rem; cursor: pointer; background: #fff; color: #333;
       border: 1px solid #ccc; padding: 0.4rem 0.9rem; border-radius: 4px; text-decoration: none;
       display: inline-block; }
.btn:hover { background: #f0f0f0; }
.btn.primary { background: #2e7d32; color: #fff; border-color: #2e7d32; font-weight: 500; }
.btn.primary:hover { background: #1b5e20; }
.btn.danger { color: #b00020; border-color: #e0a0a0; }
.btn.danger:hover { background: #fff0f0; }
.muted { color: #888; font-size: 0.82rem; }
.steps li { margin: 0.5rem 0; font-size: 0.92rem; }
.steps .ok   { color: #2e7d32; }
.steps .warn { color: #f57f17; }
.steps .err  { color: #c62828; }
.kv { display: grid; grid-template-columns: 180px 1fr; gap: 0.4rem 1rem; font-size: 0.88rem; }
.kv dt { color: #777; }
.kv dd { margin: 0; font-family: SFMono-Regular, Menlo, monospace; }
form.login { background: white; padding: 2rem; border-radius: 6px; max-width: 460px; margin: 4rem auto;
             box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
form.login label { display: block; margin: 1rem 0 0.3rem; font-weight: 600; }
form.login input { width: 100%; padding: 0.5rem; font-size: 1rem; border: 1px solid #ccc;
                   border-radius: 4px; box-sizing: border-box; font-family: inherit; }
form.login button { margin-top: 1.2rem; }
.flash { background: #fff8e1; border-left: 4px solid #ffb300; padding: 0.7rem 1rem;
         border-radius: 3px; margin-bottom: 1rem; }
.flash.error { background: #ffebee; border-left-color: #c62828; }
"""


def _header(active: str = '') -> str:
    def link(slug, label):
        cls = ' style="font-weight:600"' if slug == active else ''
        return f'<a href="/{slug}"{cls}>{label}</a>'
    return f"""
<header>
  <h1>SG/Vault — admin</h1>
  <nav>
    {link('', 'Inventory')}
    {link('setup/', 'Setup')}
    <a href="/__waker__/console" target="_blank">Console</a>
    <a href="/logout">Logout</a>
  </nav>
</header>
"""


def render_login(flash: str = '', flash_kind: str = '') -> str:
    flash_html = ''
    if flash:
        cls = 'flash error' if flash_kind == 'error' else 'flash'
        flash_html = f'<p class="{cls}">{html_lib.escape(flash)}</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SG/Vault — admin login</title>
  <style>{_CSS}</style>
</head>
<body>
<form class="login" method="POST" action="/login">
  <h1 style="text-align:center;">SG/Vault admin</h1>
  <p class="muted" style="text-align:center;">Paste your admin API key to continue.</p>
  {flash_html}
  <label for="api_key">API key</label>
  <input id="api_key" name="api_key" type="password" autocomplete="off" autofocus required>
  <button class="btn primary" type="submit" style="width:100%;">Sign in</button>
  <p class="muted" style="margin-top:1rem;font-size:0.78rem;">
    The key is the value of <code>SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE</code> on the
    waker Lambda. Run <code>sg vp setup lambda status</code> to see it.
  </p>
</form>
</body>
</html>
"""


def render_inventory(entries: list, zone: str) -> str:
    # entries: list of dicts {slug, fqdn, instance_id, public_ip, region, state}
    rows = []
    if not entries:
        rows.append('<tr><td colspan="6" style="text-align:center;color:#888;padding:2rem;">No slugs registered yet.</td></tr>')
    else:
        for e in entries:
            slug = html_lib.escape(e.get('slug', ''))
            fqdn = html_lib.escape(e.get('fqdn', ''))
            iid  = html_lib.escape(e.get('instance_id') or '—')
            ip   = html_lib.escape(e.get('public_ip')   or '—')
            reg  = html_lib.escape(e.get('region')      or '—')
            st   = e.get('state', 'unknown')
            cls  = {'running': 'ok', 'pending': 'warn', 'stopping': 'warn',
                    'stopped': 'idle', 'unknown': 'err'}.get(st, 'err')
            rows.append(
                f'<tr>'
                f'<td><a href="/slug/{slug}/"><code>{slug}</code></a></td>'
                f'<td><a href="https://{fqdn}/" target="_blank" class="mono">{fqdn}</a></td>'
                f'<td><span class="dot {cls}"></span>{html_lib.escape(st)}</td>'
                f'<td class="mono">{iid}</td>'
                f'<td class="mono">{ip}</td>'
                f'<td class="mono">{reg}</td>'
                f'</tr>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SG/Vault — Inventory</title>
  <style>{_CSS}</style>
</head>
<body>
{_header(active='')}
<p class="muted">{len(entries)} slug(s) in <code>{html_lib.escape(zone)}</code> — auto-refreshes every 30s.</p>
<table>
  <thead><tr><th>Slug</th><th>FQDN</th><th>State</th><th>Instance ID</th><th>Public IP</th><th>Region</th></tr></thead>
  <tbody id="rows">{''.join(rows)}</tbody>
</table>
<script>
  async function refresh() {{
    try {{
      const resp = await fetch('/api/v1/list', {{ cache: 'no-store', credentials: 'include' }});
      if (!resp.ok) return;
      const data = await resp.json();
      // Re-render rows in place; full page swap would lose scroll position.
      const tbody = document.getElementById('rows');
      if (!data.entries || !data.entries.length) {{
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#888;padding:2rem;">No slugs registered yet.</td></tr>';
        return;
      }}
      tbody.innerHTML = data.entries.map(e => {{
        const cls = ({{running:'ok',pending:'warn',stopping:'warn',stopped:'idle',unknown:'err'}})[e.state] || 'err';
        return `<tr>
          <td><a href="/slug/${{e.slug}}/"><code>${{e.slug}}</code></a></td>
          <td><a href="https://${{e.fqdn}}/" target="_blank" class="mono">${{e.fqdn}}</a></td>
          <td><span class="dot ${{cls}}"></span>${{e.state}}</td>
          <td class="mono">${{e.instance_id || '—'}}</td>
          <td class="mono">${{e.public_ip || '—'}}</td>
          <td class="mono">${{e.region || '—'}}</td>
        </tr>`;
      }}).join('');
    }} catch (e) {{ /* ignore — try again on next tick */ }}
  }}
  setInterval(refresh, 30000);
</script>
</body>
</html>
"""


def render_slug(slug: str, eval_steps: list, status: dict) -> str:
    rows_html = []
    for s in eval_steps:
        ok = s.get('ok')
        icon_cls = 'ok' if ok else 'err'
        icon     = '✓' if ok else '✗'
        rows_html.append(
            f'<li class="{icon_cls}">'
            f'<strong>{icon}</strong> {html_lib.escape(s.get("label", ""))} — '
            f'<span class="mono">{html_lib.escape(s.get("detail", ""))}</span>'
            f'</li>'
        )
    info_rows = []
    for k in ('slug', 'fqdn', 'stack_name', 'state', 'public_ip', 'vault_url', 'region'):
        v = status.get(k, '')
        info_rows.append(f'<dt>{html_lib.escape(k)}</dt><dd>{html_lib.escape(str(v) or "—")}</dd>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SG/Vault — {html_lib.escape(slug)}</title>
  <style>{_CSS}</style>
</head>
<body>
{_header()}
<p><a href="/" class="muted">← back to inventory</a></p>
<h2 style="margin-top:0.5rem;">{html_lib.escape(slug)}</h2>

<h3 style="font-size:1rem;color:#555;">Status</h3>
<dl class="kv">{''.join(info_rows)}</dl>

<h3 style="font-size:1rem;color:#555;margin-top:2rem;">Eval — 7 steps</h3>
<ol class="steps">{''.join(rows_html)}</ol>

<p style="margin-top:2rem;">
  <a class="btn primary" href="https://{html_lib.escape(status.get('fqdn', ''))}/" target="_blank">Open vault</a>
  <a class="btn" href="/api/v1/eval?slug={html_lib.escape(slug)}" target="_blank">Raw JSON</a>
</p>
</body>
</html>
"""
