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
import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

# Lambda Function URL — used by the warming-page JS to poll cross-origin
# instead of polling the slug FQDN (which keeps the slug FQDN's keep-alive
# socket warm and prevents DNS un-pinning). Set by Setup__Lambda at deploy
# time once the Function URL exists. Empty until the second `sg vp setup
# lambda update` after the URL is provisioned, in which case the JS falls
# back to polling the slug URL (legacy behaviour).
WAKER_LAMBDA_FUNCTION_URL = os.environ.get('WAKER_LAMBDA_FUNCTION_URL', '').rstrip('/')

# Same-zone admin/probe host — alternative cross-origin target. Defaults to
# `waker.<zone>`. Empirically may or may not defeat H2 connection coalescing
# (see library/docs/research/v0.1.14__http2-connection-coalescing.md);
# Lambda Function URL is the guaranteed-no-coalescing fallback. When BOTH
# are set, the JS prefers WAKER_PROBE_HOST so we can A/B test in production.
_DEFAULT_ZONE = os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
WAKER_PROBE_HOST = os.environ.get('WAKER_PROBE_HOST', f'waker.{_DEFAULT_ZONE}').rstrip('/')

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
                   font-weight: 500; }
    .btn.primary:hover { background: #1b5e20; border-color: #1b5e20; }
    .btn.primary[disabled] { display: none; }
    #new-tab-btn { display: none; }
    #enter-btn { display: none; }
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
    <button class="btn primary" id="new-tab-btn" onclick="openInNewTab()">Open in new tab</button>
    <button class="btn" id="enter-btn" onclick="forceEnter()">Enter (this tab)</button>
    <button class="btn danger" id="cancel-btn" onclick="cancelAll()">Cancel</button>
    <a class="btn" href="/__waker__/status?slug=__SLUG_TEXT__">View diagnostics</a>
    <a class="btn" href="/__waker__/console">Console</a>
  </div>
  <p class="status" id="status"></p>

  <script id="waker-cfg" type="application/json">__CONFIG_JSON__</script>
  <script>
    const CFG  = JSON.parse(document.getElementById('waker-cfg').textContent);
    const $    = (id) => document.getElementById(id);

    let pollT       = null;
    let countT      = null;
    let cancelled   = false;
    let startMs     = Date.now();
    let pollAttempt = 0;

    // Backoff schedule: poll fast for the first ~30s (in case vault boots
    // quickly), then back off to 60s intervals. The 60s gap is critical —
    // Chrome's HTTP/1.1 keep-alive idle timeout is ~60-90s, so 60s with no
    // requests is what lets the kept-alive socket to CloudFront actually
    // close. Polling every 5s forever would keep the socket warm forever
    // and the eventual redirect would always go via Lambda.
    function nextPollDelayMs() {
      if (pollAttempt < CFG.poll_fast_count) return CFG.poll_fast_ms;
      return CFG.poll_slow_ms;
    }

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
      // Default: poll the Lambda Function URL cross-origin so the slug
      // FQDN's socket pool slot stays idle and can drain. Only when
      // CFG.lambda_url is unset (legacy deploy without the env var) do we
      // fall back to polling the slug FQDN — at the cost of pinning the
      // socket, but functional.
      if (CFG.lambda_url) {
        const url = CFG.lambda_url + '/__waker__/probe?slug=' +
                    encodeURIComponent(CFG.slug) + '&t=' + Date.now();
        const resp = await fetch(url, {
          cache       : 'no-store',
          credentials : 'omit',
          mode        : 'cors',
          headers     : { 'X-Vault-Warming-Probe': '1' },
          redirect    : 'manual',
        });
        const json = await resp.json();
        return {
          status      : resp.status,
          waker_state : json.waker_state || '',
          ec2_state   : json.ec2_state   || '',
          via_lambda  : true,                                                   // cross-origin probe is always to Lambda; we never get "direct" detection this way
          direct_check: false,
        };
      }
      // Legacy fallback: probe the slug URL. Sets keep-alive socket so this
      // is the polling we are trying to avoid — only used when lambda_url
      // is unset.
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
        direct_check: true,                                                     // this poll can detect direct routing
      };
    }

    async function bootTick() {
      if (cancelled) return;
      pollAttempt += 1;
      let r;
      try { r = await probe(); }
      catch (e) {
        setMsg(null, 'Network error: ' + e.message, '');
        pollT = setTimeout(bootTick, nextPollDelayMs());
        return;
      }
      // Path display: when we're polling cross-origin via Lambda, we can't
      // detect direct vs proxy from the probe response (it's always Lambda).
      // Show the cross-origin polling target instead.
      if (r.direct_check) {
        setPath(r.via_lambda);
        // No X-Waker-State header → response came direct from EC2
        if (!r.via_lambda) {
          gotoNow('Direct routing detected — redirecting…');
          return;
        }
      } else {
        const target = CFG.probe_target || 'unknown';
        const label  = target === 'waker-host'  ? 'waker.<zone> (testing H2 coalescing)'
                    :  target === 'lambda-url'  ? 'Lambda Function URL (guaranteed no coalescing)'
                    :                              'slug FQDN (fallback — keeps socket warm)';
        $('path-line').textContent = 'Probe target: ' + label;
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
      // Still warming — schedule the next check with backoff cadence
      const ec2     = r.ec2_state || 'unknown';
      const nextSec = Math.round(nextPollDelayMs() / 1000);
      setMsg(null,
             'EC2 ' + ec2 + ' — vault still booting (elapsed: ' + elapsedSec() + 's)',
             'Next check in ' + nextSec + 's. Typical first-time boot is 30-90s.');
      pollT = setTimeout(bootTick, nextPollDelayMs());
    }

    function startSettleCountdown() {
      // Vault is reachable via Lambda. Wait `settle_ms` with NO network
      // activity so the browser's keep-alive socket to CloudFront idles out
      // and the Route-53 DNS cache (TTL 60s) expires. Then trigger a fresh
      // navigation that has a chance to hit the EC2 directly.
      //
      // The "Open in new tab" button is the most reliable shortcut — a new
      // tab gets its own socket pool slot and triggers fresh DNS regardless
      // of what this tab has pinned.
      $('new-tab-btn').style.display = 'inline-block';
      $('enter-btn').style.display   = 'inline-block';
      setMsg('Vault is ready',
             'Reachable via CloudFront → Lambda → EC2.',
             '');
      const settleSec = Math.round(CFG.settle_ms / 1000);
      let remaining = settleSec;
      function tick() {
        if (cancelled) return;
        if (remaining <= 0) { enterPage(); return; }
        $('detail').textContent =
          'Silently waiting ' + remaining + 's so the keep-alive socket to CloudFront idles out — ' +
          'then this tab will try a direct navigation. Or click "Open in new tab" now to skip the wait ' +
          '(new tab → fresh socket → fresh DNS lookup → direct to EC2).';
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

    function openInNewTab() {
      // A new tab uses a fresh entry in the browser's socket pool, so it
      // performs a fresh TCP connect → fresh DNS lookup. This is the most
      // reliable JS-accessible way to escape socket pinning to CloudFront.
      cancelled = true;
      clearTimeout(pollT); clearTimeout(countT);
      const url = window.location.pathname + '?_t=' + Date.now();
      const w = window.open(url, '_blank');
      if (w) {
        setMsg('Vault is ready (opened in new tab)',
               'A new tab should now be loading the vault directly.',
               'You can close this tab.');
      } else {
        setMsg('Popup blocked',
               'Your browser blocked the new tab. Click "Enter (this tab)" instead, ' +
               'or shift+click "Open in new tab" to bypass the popup blocker.',
               '');
      }
    }

    function forceEnter() { enterPage(); }

    function cancelAll() {
      cancelled = true;
      clearTimeout(pollT); clearTimeout(countT);
      $('spinner').classList.add('paused');
      $('cancel-btn').textContent = 'Cancelled';
      $('cancel-btn').disabled = true;
      $('new-tab-btn').style.display = 'inline-block';
      $('enter-btn').style.display   = 'inline-block';
      setMsg(null, 'Polling stopped.',
             'Click "Open in new tab" (most reliable — fresh socket pool), ' +
             'or "Enter (this tab)" to navigate in place.');
    }

    bootTick();
  </script>
</body>
</html>
"""


class Warming__Page(Type_Safe):
    poll_fast_ms    : int = 5000                                                      # fast cadence — first few polls while we expect a quick boot
    poll_fast_count : int = 6                                                         # number of fast polls before backing off (6 × 5s = 30s of fast polling)
    poll_slow_ms    : int = 60000                                                     # slow cadence — every 60s. The 60s gap is what lets Chrome's HTTP/1.1 keep-alive idle timeout fire on the kept-alive socket to CloudFront.
    settle_ms       : int = 90000                                                     # silent wait after vault is up — no network activity so the kept-alive socket drains before we navigate

    def render(self, slug: str) -> str:
        # probe_base — preferred cross-origin target. Order:
        #   1. WAKER_PROBE_HOST (e.g. https://waker.<zone>) — same-zone subdomain
        #      to test whether H2 coalescing actually defeats the trick
        #   2. WAKER_LAMBDA_FUNCTION_URL — guaranteed-no-coalescing fallback
        #   3. empty — JS falls back to polling the slug URL (legacy)
        probe_base = ''
        if WAKER_PROBE_HOST:
            probe_base = (WAKER_PROBE_HOST if WAKER_PROBE_HOST.startswith(('http://', 'https://'))
                          else f'https://{WAKER_PROBE_HOST}')
        elif WAKER_LAMBDA_FUNCTION_URL:
            probe_base = WAKER_LAMBDA_FUNCTION_URL
        cfg = {
            'slug'            : slug,
            'lambda_url'      : probe_base,                                          # JS still calls this field "lambda_url" but it now points at probe_base (waker.<zone> or Lambda URL)
            'probe_target'    : 'waker-host' if WAKER_PROBE_HOST else
                                ('lambda-url' if WAKER_LAMBDA_FUNCTION_URL else 'slug-fqdn'),
            'poll_fast_ms'    : self.poll_fast_ms,
            'poll_fast_count' : self.poll_fast_count,
            'poll_slow_ms'    : self.poll_slow_ms,
            'settle_ms'       : self.settle_ms,
        }
        out = _HTML_TEMPLATE
        out = out.replace('__SLUG_TEXT__'   , html_lib.escape(slug))
        out = out.replace('__CONFIG_JSON__' , json.dumps(cfg))
        return out

    def headers(self) -> dict:
        return dict(NO_CACHE_HEADERS)
