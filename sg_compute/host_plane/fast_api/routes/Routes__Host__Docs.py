# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Docs
#
# GET /docs-auth?apikey={key}
#   Serves Swagger UI with the host API key pre-injected as a requestInterceptor.
#   The UI loads this in an iframe — iframe origin is the sidecar, so /openapi.json
#   is same-origin and no CORS is needed for Swagger itself to work.
#
# GET /host/shell/page
#   Serves an xterm.js terminal page that connects WS to /host/shell/stream
#   same-origin, so the auth cookie (set via /auth/set-cookie-form) is sent
#   automatically by the browser — no header needed, no cross-origin WS issue.
#   Admin UI Terminal tab uses an iframe to this page.
#
# Both registered at root (prefix='/') and excluded from the OpenAPI schema.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from fastapi                                                                    import Query
from fastapi.responses                                                          import HTMLResponse
from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix     import Safe_Str__Fast_API__Route__Prefix


TAG__ROUTES_HOST_DOCS = 'host'

DOCS_AUTH_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Host Control — API Docs</title>
  <link rel="stylesheet"
        href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body {{ margin: 0; }}
    .topbar {{ display: none !important; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    const apiKey = {api_key_json};
    SwaggerUIBundle({{
      url:             '/openapi.json',
      dom_id:          '#swagger-ui',
      presets:         [SwaggerUIBundle.presets.apis],
      tryItOutEnabled: true,
      persistAuthorization: true,
      requestInterceptor: function(req) {{
        if (apiKey) req.headers['X-API-Key'] = apiKey;
        return req;
      }},
    }});
  </script>
</body>
</html>"""


SHELL_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Host Shell</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 100%; height: 100%; background: #0f0f1a; overflow: hidden; }
    #terminal { width: 100%; height: 100%; }
    #auth-prompt {
      position: absolute; inset: 0; display: flex; flex-direction: column;
      align-items: center; justify-content: center; gap: 16px;
      background: #0f0f1a; color: #a0a0c0; font-family: system-ui, sans-serif;
    }
    #auth-prompt h2 { font-size: 16px; color: #e8e8f0; }
    #auth-prompt p  { font-size: 13px; text-align: center; max-width: 360px; line-height: 1.5; }
    #auth-prompt a  { color: #7c6af7; text-decoration: none; font-weight: 600; }
    #auth-prompt a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div id="auth-prompt" style="display:none">
    <h2>🔑 Authentication required</h2>
    <p>Set the API key cookie to enable the terminal.</p>
    <a href="/auth/set-cookie-form">Open authentication form →</a>
    <p style="font-size:11px;color:#666">After authenticating, reload this page.</p>
  </div>
  <div id="terminal"></div>
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
  <script>
    const term = new Terminal({ theme: { background: '#0f0f1a', foreground: '#e8e8f0',
      cursor: '#7c6af7', selectionBackground: 'rgba(124,106,247,0.3)' },
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 13, cursorBlink: true });
    const fit  = new FitAddon.FitAddon();
    term.loadAddon(fit);
    term.open(document.getElementById('terminal'));
    fit.fit();
    window.addEventListener('resize', () => fit.fit());

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws    = new WebSocket(`${proto}//${location.host}/host/shell/stream`);
    ws.binaryType = 'arraybuffer';

    ws.onopen  = () => term.write('\\r\\n\\x1b[32m\\u2713 Connected\\x1b[0m\\r\\n');
    ws.onmessage = (e) => {
      const buf = e.data instanceof ArrayBuffer ? new Uint8Array(e.data) : new TextEncoder().encode(e.data);
      term.write(buf);
    };
    ws.onclose = (e) => {
      if (e.code === 1006 || e.code === 1008) {
        document.getElementById('terminal').style.display = 'none';
        document.getElementById('auth-prompt').style.display = 'flex';
      } else {
        term.write('\\r\\n\\x1b[31m\\u2717 Disconnected\\x1b[0m\\r\\n');
      }
    };
    ws.onerror  = () => term.write('\\r\\n\\x1b[31m\\u2717 Connection error\\x1b[0m\\r\\n');
    term.onData = (data) => ws.readyState === 1 && ws.send(new TextEncoder().encode(data));
  </script>
</body>
</html>"""


class Routes__Host__Docs(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_DOCS

    def setup_routes(self):
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')
        router = self.router

        @router.get('/docs-auth', include_in_schema=False)
        async def docs_auth(apikey: str = Query(default="")):
            html = DOCS_AUTH_TEMPLATE.format(api_key_json=json.dumps(apikey))
            return HTMLResponse(content=html)

        @router.get('/host/shell/page', include_in_schema=False)
        async def shell_page():
            return HTMLResponse(content=SHELL_PAGE_HTML)
