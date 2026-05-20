# ═══════════════════════════════════════════════════════════════════════════════
# sg_edge edge-waker — Loading__Page
# The cold-cold UX: CloudFront fails over to the Edge Waker secondary when the
# proxy fleet is at zero. The waker returns this HTML immediately while the fleet
# boots in the background. The page polls /__edge__/status every 2s and reloads
# itself once a proxy is serving (status.ready == true), at which point the
# request hits the warm path through CloudFront's primary origin. No external
# assets — single self-contained document so it renders before anything else is up.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

_TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Starting up…</title>
<style>
 body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0;
        display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0 }}
 .card {{ text-align:center; max-width:30rem; padding:2rem }}
 .spinner {{ width:2.5rem; height:2.5rem; margin:1rem auto; border:3px solid #334155;
             border-top-color:#38bdf8; border-radius:50%; animation:spin 1s linear infinite }}
 @keyframes spin {{ to {{ transform:rotate(360deg) }} }}
 small {{ color:#64748b }}
</style></head>
<body><div class="card">
 <div class="spinner"></div>
 <h1>Spinning up infrastructure…</h1>
 <p>This edge was idle and is starting back up. It usually takes under a minute.</p>
 <small>SG/Edge waker v{version}</small>
</div>
<script>
 (function () {{
   function poll() {{
     fetch('/__edge__/status', {{cache:'no-store'}})
       .then(function (r) {{ return r.json(); }})
       .then(function (s) {{ if (s && s.ready) {{ window.location.reload(); }} }})
       .catch(function () {{}});
   }}
   setInterval(poll, 2000);
 }})();
</script>
</body></html>"""


class Loading__Page(Type_Safe):

    def render(self, version: str = '') -> str:
        return _TEMPLATE.format(version=version or 'dev')
