# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Auth
#
# GET  /auth/set-cookie-form  → HTML form (no auth required)
# POST /auth/set-auth-cookie  → sets api-key cookie for this origin (no auth)
#
# Both paths are excluded from the api-key middleware so the user can set the
# cookie before authenticating. Once the cookie is set, the middleware accepts
# it as a fallback to the X-API-Key header (Middleware__Check_API_Key already
# checks cookies: api_key = header OR cookie).
#
# Primary use-case: the node-detail Terminal tab opens this form in a new window
# once per browser session. After that, the /host/shell/page iframe (same-origin)
# connects the WS terminal with the cookie — no header needed.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                                                                    import Request
from fastapi.responses                                                          import HTMLResponse, JSONResponse
from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix     import Safe_Str__Fast_API__Route__Prefix

TAG__ROUTES_HOST_AUTH = 'host'

AUTH_FORM_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Host API — Authenticate</title>
  <style>
    :root {{
      --bg: #0f0f1a; --panel: #1a1a2e; --elev: #252540;
      --text: #e8e8f0; --text2: #a0a0c0; --accent: #7c6af7;
      --good: #4ade80; --bad: #f87171; --border: #2a2a4a;
      --mono: 'JetBrains Mono', 'Fira Code', monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
    .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
             padding: 32px; width: 480px; max-width: 95vw; display: flex; flex-direction: column; gap: 20px; }}
    h1 {{ font-size: 18px; font-weight: 600; }}
    .sub {{ font-size: 13px; color: var(--text2); line-height: 1.5; }}
    .key-name {{ background: var(--elev); border: 1px solid var(--border); border-radius: 6px;
                 padding: 8px 12px; font-family: var(--mono); font-size: 12px; color: var(--accent); }}
    label {{ font-size: 12px; color: var(--text2); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }}
    input {{ width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px;
             background: var(--elev); color: var(--text); font-family: var(--mono); font-size: 13px;
             outline: none; transition: border-color 150ms; }}
    input:focus {{ border-color: var(--accent); }}
    button {{ padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px;
              font-weight: 600; cursor: pointer; transition: opacity 150ms; }}
    .btn-set {{ background: var(--accent); color: #fff; width: 100%; }}
    .btn-set:hover {{ opacity: .9; }}
    .btn-clear {{ background: var(--elev); color: var(--text2); border: 1px solid var(--border);
                  font-size: 12px; padding: 6px 14px; }}
    .msg {{ font-size: 13px; padding: 8px 12px; border-radius: 6px; display: none; }}
    .msg.ok  {{ background: rgba(74,222,128,.12); color: var(--good); border: 1px solid rgba(74,222,128,.3); }}
    .msg.err {{ background: rgba(248,113,113,.12); color: var(--bad);  border: 1px solid rgba(248,113,113,.3); }}
    .row {{ display: flex; gap: 8px; align-items: center; }}
    .existing {{ font-size: 11px; color: var(--text2); }}
  </style>
</head>
<body>
<div class="card">
  <div>
    <h1>🔑 Authenticate — Host API</h1>
    <p class="sub" style="margin-top:8px">
      Set a browser cookie for this sidecar so the terminal and API
      work without sending the header on every request.
    </p>
  </div>

  <div>
    <div style="font-size:12px;color:var(--text2);margin-bottom:6px">Cookie / header name</div>
    <div class="key-name" id="key-name">{key_name}</div>
  </div>

  <div style="display:flex;flex-direction:column;gap:8px">
    <label for="key-input">API Key value</label>
    <input id="key-input" type="password" placeholder="Paste the API key here…" autocomplete="off">
  </div>

  <div class="row">
    <button class="btn-set" onclick="setKey()">Set Cookie &amp; Authenticate</button>
    <button class="btn-clear" onclick="clearKey()">Clear Cookie</button>
  </div>

  <div class="msg" id="msg"></div>
  <div class="existing" id="existing"></div>
</div>
<script>
  const KEY_NAME = document.getElementById('key-name').textContent.trim();

  function showMsg(text, type) {{
    const el = document.getElementById('msg');
    el.textContent = text; el.className = 'msg ' + type; el.style.display = 'block';
  }}

  function checkExisting() {{
    const el = document.getElementById('existing');
    const all = document.cookie.split(';').map(c => c.trim());
    const found = all.find(c => c.startsWith(KEY_NAME + '='));
    el.textContent = found ? '✓ Cookie already set for this session.' : '';
  }}

  async function setKey() {{
    const val = document.getElementById('key-input').value.trim();
    if (!val) {{ showMsg('Please enter the API key value.', 'err'); return; }}
    const resp = await fetch('/auth/set-auth-cookie', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ cookie_value: val }}),
    }});
    if (resp.ok) {{
      showMsg('✓ Cookie set — returning to terminal…', 'ok');
      setTimeout(() => {{ window.location.href = '/host/shell/page'; }}, 800);
    }} else {{
      showMsg('✗ Failed to set cookie (HTTP ' + resp.status + ')', 'err');
    }}
  }}

  async function clearKey() {{
    await fetch('/auth/set-auth-cookie', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ cookie_value: '' }}),
    }});
    showMsg('Cookie cleared.', 'ok');
    checkExisting();
  }}

  document.getElementById('key-input').addEventListener('keydown', e => {{
    if (e.key === 'Enter') setKey();
  }});
  checkExisting();
</script>
</body>
</html>"""


class Routes__Host__Auth(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_AUTH

    def setup_routes(self):
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')
        router = self.router

        @router.get('/auth/set-cookie-form', include_in_schema=False)
        async def set_cookie_form():
            key_name = os.environ.get('FAST_API__AUTH__API_KEY__NAME', 'X-API-Key')
            html = AUTH_FORM_HTML.format(key_name=key_name)
            return HTMLResponse(content=html)

        @router.post('/auth/set-auth-cookie', include_in_schema=False)
        async def set_auth_cookie(request: Request):
            body      = await request.json()
            key_name  = os.environ.get('FAST_API__AUTH__API_KEY__NAME', 'X-API-Key')
            key_value = str(body.get('cookie_value', ''))
            response  = JSONResponse({'ok': True})
            if key_value:
                response.set_cookie(key      = key_name  ,
                                    value    = key_value ,
                                    httponly = False      ,   # must be readable by the WS handshake (browser sends it automatically)
                                    samesite = 'lax'     ,   # same-origin pages (shell/page iframe) get it; cross-origin fetch does not
                                    max_age  = 86400     )   # 24h
            else:
                response.delete_cookie(key=key_name)
            return response
