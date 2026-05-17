# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Warming__Page
# Generates the "vault is warming up" HTML page returned while the EC2 instance
# starts. Includes auto-refresh meta so the browser retries automatically.
# No-cache headers prevent CDN/browser from caching the intermediate state.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma'       : 'no-cache',
    'Expires'      : '0',
    'Content-Type' : 'text/html; charset=utf-8',
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="{refresh_seconds}">
  <title>Vault warming up…</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      min-height: 100vh; margin: 0;
      background: #f5f5f5; color: #333;
    }}
    .spinner {{
      width: 48px; height: 48px; border: 4px solid #ccc;
      border-top-color: #555; border-radius: 50%;
      animation: spin 1s linear infinite; margin-bottom: 1.5rem;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    h1 {{ font-size: 1.4rem; margin: 0 0 .5rem; }}
    p  {{ font-size: .9rem; color: #777; }}
  </style>
</head>
<body>
  <div class="spinner"></div>
  <h1>Vault is warming up</h1>
  <p>Slug: <code>{slug}</code></p>
  <p>This page will refresh automatically every {refresh_seconds} seconds.</p>
</body>
</html>
"""


class Warming__Page(Type_Safe):
    refresh_seconds : int = 10

    def render(self, slug: str) -> str:
        return _HTML_TEMPLATE.format(slug=slug, refresh_seconds=self.refresh_seconds)

    def headers(self) -> dict:
        return dict(NO_CACHE_HEADERS)
