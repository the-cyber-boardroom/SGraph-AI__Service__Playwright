# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Warming__Page
# "Vault is warming up" HTML page returned while the EC2 instance starts.
# Auto-refresh meta drives the browser to retry every N seconds; "Cancel"
# stops it with a click; "View diagnostics" links to the operator console.
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
  <meta id="auto-refresh" http-equiv="refresh" content="{refresh_seconds}">
  <title>Vault warming up — {slug}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
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
    .spinner.paused {{ animation-play-state: paused; opacity: 0.3; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    h1 {{ font-size: 1.4rem; margin: 0 0 .5rem; }}
    p  {{ font-size: .9rem; color: #777; margin: .25rem 0; }}
    .actions {{ margin-top: 1.5rem; display: flex; gap: .75rem; }}
    .btn {{
      font-family: inherit; font-size: .85rem; cursor: pointer;
      background: #fff; color: #333; border: 1px solid #ccc;
      padding: .45rem .9rem; border-radius: 4px; text-decoration: none;
    }}
    .btn:hover {{ background: #f0f0f0; border-color: #aaa; }}
    .btn.danger {{ color: #b00020; border-color: #e0a0a0; }}
    .btn.danger:hover {{ background: #fff0f0; }}
    .status {{ font-size: .8rem; color: #999; margin-top: 1rem; min-height: 1rem; }}
  </style>
</head>
<body>
  <div class="spinner" id="spinner"></div>
  <h1>Vault is warming up</h1>
  <p>Slug: <code>{slug}</code></p>
  <p id="refresh-msg">This page will refresh automatically every {refresh_seconds} seconds.</p>
  <div class="actions">
    <button class="btn danger" id="cancel-btn"
            onclick="cancelRefresh();">Cancel auto-refresh</button>
    <a class="btn" href="/__waker__/status?slug={slug}">View diagnostics</a>
    <a class="btn" href="/__waker__/console">Console</a>
  </div>
  <p class="status" id="status"></p>
  <script>
    function cancelRefresh() {{
      var meta = document.getElementById('auto-refresh');
      if (meta) meta.parentNode.removeChild(meta);
      document.getElementById('spinner').classList.add('paused');
      document.getElementById('refresh-msg').textContent = 'Auto-refresh stopped.';
      document.getElementById('cancel-btn').textContent = 'Cancelled';
      document.getElementById('cancel-btn').disabled = true;
      document.getElementById('status').textContent = 'You can reload manually or use the links above.';
    }}
  </script>
</body>
</html>
"""


class Warming__Page(Type_Safe):
    refresh_seconds : int = 10

    def render(self, slug: str) -> str:
        return _HTML_TEMPLATE.format(slug=slug, refresh_seconds=self.refresh_seconds)

    def headers(self) -> dict:
        return dict(NO_CACHE_HEADERS)
