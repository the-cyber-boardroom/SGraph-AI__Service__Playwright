# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Warming__Page
# JS-driven "Vault is warming up" page. No <meta http-equiv="refresh"> — the
# page polls the current URL with fetch() and inspects the X-Waker-State
# response header to decide what to do.
#
#   X-Waker-State = warming   → keep polling (EC2 still booting)
#   X-Waker-State = proxied   → Lambda is now successfully proxying to the EC2.
#                                Start a countdown for `settle_ms` then trigger
#                                window.location.replace(). The wait lets the
#                                browser's HTTP/1.1 keep-alive socket to
#                                CloudFront idle out + Route-53 60s TTL DNS
#                                cache expire, giving the next navigation a
#                                chance to land directly on the EC2 IP.
#   (no X-Waker-State header) → response came direct from EC2 — redirect now.
#
# Why the wait matters — see team/comms/briefs/v0.1.14__browser-dns-pinning/.
# Browsers do not just cache DNS records; they also pool TCP connections per
# (scheme, host, port). Once a socket to a host is open and idle-eligible, the
# next request reuses it regardless of any DNS change. There is no JS API to
# force socket close — only time + lack of traffic does it.
# ═══════════════════════════════════════════════════════════════════════════════

import html as html_lib
import json

from osbot_utils.type_safe.Type_Safe import Type_Safe

NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma'       : 'no-cache',
    'Expires'      : '0',
    'Content-Type' : 'text/html; charset=utf-8',
}

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Vault warming up — __SLUG_TEXT__</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
           display: flex; flex-direction: column; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; background: #f5f5f5; color: #333; padding: 1rem; }
    .spinner { width: 48px; height: 48px; border: 4px solid #ccc;
               border-top-color: #555; border-radius: 50%;
               animation: spin 1s linear infinite; margin-bottom: 1.5rem; }
    .spinner.paused { animation-play-state: paused; opacity: 0.3; }
    @keyframes spin { to { transform: rotate(360deg); } }
    h1 { font-size: 1.4rem; margin: 0 0 .5rem; }
    p { font-size: .9rem; color: #555; margin: .25rem 0; text-align: center; }
    p.dim { font-size: .82rem; color: #888; }
    p.path { font-size: .78rem; color: #888; font-family: SFMono-Regular, Menlo, monospace; }
    p.path.direct { color: #2e7d32; font-weight: 500; }
    .actions { margin-top: 1.5rem; display: flex; gap: .75rem; flex-wrap: wrap; justify-content: center; }
    .btn { font-family: inherit; font-size: .85rem; cursor: pointer;
           background: #fff; color: #333; border: 1px solid #ccc;
           padding: .45rem .9rem; border-radius: 4px; text-decoration: none; }
    .btn:hover { background: #f0f0f0; border-color: #aaa; }
    .btn.primary { background: #2e7d32; color: #fff; border-color: #2e7d32;
                   font-weight: 500; display: none; }
    .btn.primary:hover { background: #1b5e20; border-color: #1b5e20; }
    .btn.danger { color: #b00020; border-color: #e0a0a0; }
    .btn.danger:hover { background: #fff0f0; }
    .btn:disabled { color: #999; cursor: not-allowed; background: #f7f7f7; }
    .status { font-size: .8rem; color: #999; margin-top: 1rem; min-height: 1rem; text-align: center; }
    .status.error { color: #b00020; font-weight: 500; }
    code { background: #eee; padding: 1px 5px; border-radius: 3px;
           font-family: SFMono-Regular, Menlo, monospace; font-size: .82rem; }
  </style>
</head>
<body>
  <div class="spinner" id="spinner"></div>
  <h1 id="title">Vault is warming up</h1>
  <p>Slug: <code>__SLUG_TEXT__</code></p>
  <p id="phase-msg">Initialising…</p>
  <p id="detail" class="dim"></p>
  <p id="path-line" class="path"></p>

  <div class="actions">
    <button class="btn primary" id="enter-btn" onclick="forceEnter()">Enter now</button>
    <button class="btn danger" id="cancel-btn" onclick="cancelAll()">Cancel</button>
    <a class="btn" href="/__waker__/status?slug=__SLUG_TEXT__">View diagnostics</a>
    <a class="btn" href="/__waker__/console">Console</a>
  </div>
  <p class="status" id="status"></p>

  <script id="waker-cfg" type="application/json">__CONFIG_JSON__</script>
  <script>
    const CFG  = JSON.parse(document.getElementById('waker-cfg').textContent);
    const $    = (id) => document.getElementById(id);

    let pollT     = null;
    let countT    = null;
    let cancelled = false;
    let startMs   = Date.now();

    function elapsedSec() { return Math.round((Date.now() - startMs) / 1000); }
    function setMsg(title, msg, detail) {
      if (title  !== null) $('title').textContent = title;
      if (msg    !== null) $('phase-msg').textContent = msg;
      if (detail !== null) $('detail').textContent = detail;
    }
    function setPath(viaLambda) {
      const el = $('path-line');
      if (viaLambda === null) { el.textContent = ''; el.classList.remove('direct'); return; }
      if (viaLambda) {
        el.textContent = 'Currently routing via: CloudFront → Lambda → EC2';
        el.classList.remove('direct');
      } else {
        el.textContent = 'Currently routing: direct to EC2';
        el.classList.add('direct');
      }
    }

    async function probe() {
      // Fetch the same URL the user originally navigated to. Lambda returns
      // either the warming page (state=warming) or proxies to the vault
      // (state=proxied). When DNS converges, the same fetch goes direct to
      // EC2 and the X-Waker-State header is absent.
      const url = window.location.pathname + '?_probe=' + Date.now();
      const resp = await fetch(url, {
        cache       : 'no-store',
        credentials : 'omit',
        headers     : { 'X-Vault-Warming-Probe': '1' },
        redirect    : 'manual',
      });
      return {
        status      : resp.status,
        waker_state : resp.headers.get('x-waker-state'),
        ec2_state   : resp.headers.get('x-waker-ec2-state'),
        via_lambda  : !!resp.headers.get('x-waker-state'),
      };
    }

    async function bootTick() {
      if (cancelled) return;
      let r;
      try { r = await probe(); }
      catch (e) {
        setMsg(null, 'Network error: ' + e.message, '');
        pollT = setTimeout(bootTick, CFG.poll_ms);
        return;
      }
      setPath(r.via_lambda);

      // No X-Waker-State header → response came direct from EC2
      if (!r.via_lambda) {
        gotoNow('Direct routing detected — redirecting…');
        return;
      }
      if (r.waker_state === 'not_found' || r.waker_state === 'error') {
        setMsg('Vault not found',
               'Slug "' + CFG.slug + '" is not registered or the waker reported an error.',
               'Click View diagnostics for the full request.');
        $('spinner').classList.add('paused');
        $('status').className = 'status error';
        $('status').textContent = 'Polling stopped.';
        return;
      }
      if (r.waker_state === 'proxied') {
        // Vault is up — switch to settle countdown
        startSettleCountdown();
        return;
      }
      // Still warming
      const ec2 = r.ec2_state || 'unknown';
      setMsg(null,
             'EC2 ' + ec2 + ' — vault still booting (elapsed: ' + elapsedSec() + 's)',
             'Lambda is checking every ' + (CFG.poll_ms/1000) + 's. Typical boot: 30-90s.');
      pollT = setTimeout(bootTick, CFG.poll_ms);
    }

    function startSettleCountdown() {
      // Vault is reachable via Lambda. Wait `settle_ms` with no network
      // activity so the browser's keep-alive socket to CloudFront idles out
      // and the Route-53 DNS cache (TTL 60s) expires. Then trigger a fresh
      // navigation that has a chance to hit the EC2 directly.
      $('enter-btn').style.display = 'inline-block';
      setMsg('Vault is ready',
             'Reachable now via CloudFront → Lambda → EC2.',
             '');
      const settleSec = Math.round(CFG.settle_ms / 1000);
      let remaining = settleSec;
      function tick() {
        if (cancelled) return;
        if (remaining <= 0) { enterPage(); return; }
        $('detail').textContent = 'Waiting ' + remaining + 's for browser DNS cache + socket pool to drain so the next navigation can go direct to EC2 (or click Enter now to use Lambda).';
        remaining -= 1;
        countT = setTimeout(tick, 1000);
      }
      tick();
    }

    function gotoNow(reason) {
      cancelled = true;
      clearTimeout(pollT); clearTimeout(countT);
      setMsg(null, reason, '');
      window.location.replace(window.location.pathname + '?_t=' + Date.now());
    }

    function enterPage() {
      cancelled = true;
      clearTimeout(pollT); clearTimeout(countT);
      window.location.replace(window.location.pathname + '?_t=' + Date.now());
    }

    function forceEnter() { enterPage(); }

    function cancelAll() {
      cancelled = true;
      clearTimeout(pollT); clearTimeout(countT);
      $('spinner').classList.add('paused');
      $('cancel-btn').textContent = 'Cancelled';
      $('cancel-btn').disabled = true;
      $('enter-btn').style.display = 'inline-block';
      setMsg(null, 'Polling stopped.',
             'Reload manually, or click Enter now to navigate via current path.');
    }

    bootTick();
  </script>
</body>
</html>
"""


class Warming__Page(Type_Safe):
    poll_ms   : int = 5000                                                            # active poll cadence while EC2 is booting (5s)
    settle_ms : int = 60000                                                           # silent wait after vault is up so the keep-alive socket can idle out + DNS cache expires (60s)

    def render(self, slug: str) -> str:
        cfg = {
            'slug'      : slug,
            'poll_ms'   : self.poll_ms,
            'settle_ms' : self.settle_ms,
        }
        out = _HTML_TEMPLATE
        out = out.replace('__SLUG_TEXT__'   , html_lib.escape(slug))
        out = out.replace('__CONFIG_JSON__' , json.dumps(cfg))
        return out

    def headers(self) -> dict:
        return dict(NO_CACHE_HEADERS)
