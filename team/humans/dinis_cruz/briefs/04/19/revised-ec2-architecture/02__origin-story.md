# [EC2] The Origin Story — How We Got to the Sidecar Design

**Runtime context:** Investigation ran on EC2. The bug itself also affects Lambda (same Playwright + same authenticated upstream = same hang), but the sidecar workaround documented here is EC2-only by construction. Lambda's path forward for authenticated proxies is separately scoped out in `01__architecture.md`.
**Status:** Historical — preserved reasoning chain
**Date:** 2026-04-20
**Based on:** Phase 1.1–1.12 investigation in `../debug-session/`

> **Note on this document.** This was originally the proposed-solution doc, written when the sidecar pattern was a narrow fix for a specific proxy-auth bug. The scope has since expanded — see `01__architecture.md` for the current architecture that treats the sidecar as a full HTTP gateway. This document is kept because the bug-investigation reasoning remains useful: anyone who wants to verify that the architecture is empirically grounded should read this plus the phase notes it references.
>
> **If you are trying to implement the architecture, go to `01__architecture.md`.**
> **If you want to understand why that architecture is the right one, continue here.**

---

## TL;DR

The authenticated upstream proxy breaks Playwright browsers when they hit its authenticated path (observed empirically on EC2; same failure mode applies on Lambda based on the underlying bug mechanism). curl works through it, browsers don't. The root cause is a specific interaction between browsers' TLS-retry-after-error pattern and the upstream's addon/FastAPI pipeline — but we don't need to fix the upstream to unblock the service.

**Proposed fix (narrow — now subsumed by `01__architecture.md`):** run a small mitmdump sidecar inside the Playwright container. The browser talks to the sidecar over loopback (no auth from the browser's perspective). The sidecar forwards to the upstream proxy with preemptive authentication, exactly like curl. Works identically for Chromium, Firefox, and WebKit. No CDP gymnastics. No per-browser special casing. **EC2-only**; Lambda's execution model doesn't admit a persistent sidecar process.

Phase 1.11 confirmed this with real traffic: Chromium nav went from 30s timeout to 235ms.

---

## Why the current code doesn't work

`sgraph_ai_service_playwright/service/Browser__Launcher.py` currently has this logic:

```python
def build_proxy_dict(self, proxy, browser_name):
    out = {'server': str(proxy.server)}
    if proxy.auth is not None and browser_name != Enum__Browser__Name.CHROMIUM:
        out['username'] = str(proxy.auth.username)
        out['password'] = str(proxy.auth.password)
    return out
```

For Firefox/WebKit, it passes credentials to `launch(proxy={...})` hoping the browser will handle 407 challenges natively. For Chromium, it leaves `auth=None` and relies on `Proxy__Auth__Binder.py` to wire CDP `Fetch.authRequired` handlers.

**Neither works against the upstream proxy on EC2.** Phase 1.10 showed all three browsers fail identically — 20-second timeout, about:blank, empty HTML — regardless of which approach we use.

Phase 1.9 showed all three browsers work against a fresh local mitmproxy 12.2.2. Same browsers, same Playwright, same code — different upstream. The problem lives in the upstream, not in our stack.

---

## Architecture

### Current (broken on EC2)

```
┌──────────────────────┐         ┌─────────────────────────────┐
│ Playwright container │         │ Authenticated upstream      │
│                      │         │ proxy  (HTTP Basic, 407)    │
│  ┌────────────────┐  │         │                             │
│  │ Browser        │──┼────────▶│  407 challenge              │
│  │ (Chromium)     │  │         │  addon pipeline             │
│  │ creds in       │◀─┼─────────│  (custom interceptor +      │
│  │ launch kwargs  │  │  403    │   FastAPI integration)      │
│  └────────────────┘  │  hang   │                             │
│                      │  20-30s └─────────────────────────────┘
└──────────────────────┘
```

Browser → direct to the upstream. Browser sends CONNECT without auth. Upstream returns 407. Browser retries with credentials. Something in the upstream's addon pipeline breaks the retry path. Browser hangs, times out, renders about:blank.

### Proposed (works — proven in Phase 1.11)

```
┌────────────────────────────────────────────────┐         ┌─────────────────────────────┐
│ Playwright container                           │         │ Authenticated upstream      │
│                                                │         │ proxy  (unchanged)          │
│  ┌────────────────┐   ┌──────────────────────┐ │         │                             │
│  │ Browser        │   │ Sidecar mitmdump     │ │         │                             │
│  │ (any)          │──▶│ 127.0.0.1:8890       │─┼────────▶│ Preemptive Basic auth on    │
│  │                │   │ mode=upstream        │ │         │ every CONNECT               │
│  │ no creds       │◀──│ upstream_auth=u:p    │◀┼─────────│ 200 Connection established  │
│  │ server=local   │   │                      │ │         │                             │
│  └────────────────┘   └──────────────────────┘ │         └─────────────────────────────┘
│                                                │                ✓ works like curl
└────────────────────────────────────────────────┘
```

Browser sees only a clean, loopback, no-auth proxy. The sidecar holds the credentials. Each forward from the sidecar to the upstream is a fresh, stateless, curl-style preemptively-authenticated CONNECT. The upstream's addon pipeline sees traffic it already handles correctly.

---

## Request flow — proposed path

### Happy path: first page load

```
Browser                 Sidecar mitmdump               Upstream proxy              Target
(Chromium/FF/WK)        (127.0.0.1:8890)              (auth-enforcing)            (example.com)
      │                        │                              │                       │
      │  CONNECT example.com   │                              │                       │
      │───────────────────────▶│                              │                       │
      │                        │   CONNECT example.com        │                       │
      │                        │   Proxy-Authorization: Basic │                       │
      │                        │   (preemptive, always)       │                       │
      │                        │─────────────────────────────▶│                       │
      │                        │       200 Connection OK      │                       │
      │                        │◀─────────────────────────────│                       │
      │    200 Connection OK   │                              │                       │
      │◀───────────────────────│                              │                       │
      │                        │                              │                       │
      │          ─ ─ ─ TLS handshake (end-to-end) ─ ─ ─       │                       │
      │                        │                              │                       │
      │      GET /             │       forward GET /          │    GET /              │
      │───────────────────────▶│─────────────────────────────▶│──────────────────────▶│
      │                        │                              │                       │
      │      200 OK            │         200 OK               │    200 OK             │
      │◀───────────────────────│◀─────────────────────────────│◀──────────────────────│
      │                        │                              │                       │
```

### Chromium's TLS-retry case (observed in Phase 1.11 log)

```
Browser                 Sidecar                       Upstream
  │                        │                            │
  │  CONNECT example.com   │                            │
  │───────────────────────▶│                            │
  │                        │  CONNECT + preemptive auth │
  │                        │───────────────────────────▶│
  │                        │       200                  │
  │                        │◀───────────────────────────│
  │    200                 │                            │
  │◀───────────────────────│                            │
  │                        │                            │
  │   ─ ─ TLS ClientHello ─│                            │
  │                        │  ─ ─ Forged cert ─ ─       │
  │◀ ─ ─ ServerHello + cert│                            │
  │                        │                            │
  │ ✗ TLS alert:           │                            │
  │   certificate unknown  │                            │
  │ [drops connection]     │                            │
  │                        │                            │
  │ [reconnects, attempt 2]│                            │
  │  CONNECT example.com   │                            │
  │───────────────────────▶│                            │
  │                        │  CONNECT + preemptive auth │   ← FRESH connection
  │                        │───────────────────────────▶│   ← FRESH auth header
  │                        │       200                  │
  │                        │◀───────────────────────────│
  │                        │                            │
  │  GET / → 200 OK        │                            │
  │◀══════════════════════▶│                            │
```

The key point: the upstream sees each forward as an independent preemptively-authenticated request. No 407 challenge, no retry state to preserve, no addon pipeline confusion.

---

## What breaks in the direct path (for posterity)

Phase 1.8 captured the failure in detail via `Network.enable`:

```
Browser (direct to the upstream)          Upstream proxy
   │                                    │
   │ CONNECT example.com                │
   │───────────────────────────────────▶│
   │                                    │  407 Proxy Authentication Required
   │◀───────────────────────────────────│  Proxy-Authenticate: Basic realm=mitmproxy
   │                                    │
   │ [CDP handler: continueWithAuth]    │
   │ (or: browser's native auth retry)  │
   │                                    │
   │ CONNECT with Proxy-Authorization   │
   │───────────────────────────────────▶│
   │                                    │  ✗ addon pipeline breaks here
   │          ⋯ silence ⋯                │
   │                                    │
   │  [30s later]                       │
   │  Network.loadingFailed             │
   │  errorText: net::ERR_TIMED_OUT     │
   │  canceled: False                   │
```

Only ONE `Network.requestWillBeSent` event for the entire nav. The retry doesn't even appear at the browser's network layer — Chromium accepts the auth reply via CDP but never acts on it. The upstream's addon pipeline apparently doesn't produce the response Chromium expects to unblock the retry.

curl sidesteps this because it sends `Proxy-Authorization` preemptively on the first CONNECT — no challenge, no retry, no addon-pipeline-traversal-across-retries.

---

## Implementation plan

### Step 1 — Bake mitmproxy into Layer 3

In the Lambda Layer build (`docker/layer-3-deps/`):

```dockerfile
RUN pip install --no-cache-dir mitmproxy==12.2.2
```

Size impact: ~15 MB. mitmproxy 12.2.2 is the version validated in Phase 1.9 and 1.11.

### Step 2 — Config additions

New env var contract for the sidecar:

```
SG_PLAYWRIGHT__SIDECAR_PROXY_ENABLED   = 'true' | 'false'     (default: 'true' when MITM_PROXY_URL set)
SG_PLAYWRIGHT__SIDECAR_PROXY_PORT      = int                  (default: 8890)
SG_PLAYWRIGHT__MITM_PROXY_URL          = http://host:port     (upstream — was previously read by the browser)
SG_PLAYWRIGHT__MITM_PROXY_USER         = str                  (upstream creds — stays server-side)
SG_PLAYWRIGHT__MITM_PROXY_PASS         = str                  (upstream creds — stays server-side)
```

The credentials move from "passed to browser" to "held in sidecar config." No client ever sees them.

### Step 3 — Startup hook

New module `sgraph_ai_service_playwright/service/Sidecar__Proxy.py`:

```python
class Sidecar__Proxy(Type_Safe):
    port           : int
    upstream_url   : str
    upstream_user  : str
    upstream_pass  : str
    process        : subprocess.Popen = None
    startup_log    : Path

    def start(self) -> Self:
        # Use setsid + </dev/null to prevent mitmdump's TTY-hang
        cmd = ['setsid', 'mitmdump',
               '--listen-host', '127.0.0.1',
               '--listen-port', str(self.port),
               '--mode', f'upstream:{self.upstream_url}',
               '--set', f'upstream_auth={self.upstream_user}:{self.upstream_pass}',
               '--ssl-insecure',
               '--set', 'block_global=false']
        self.process = subprocess.Popen(cmd,
                                         stdin  = subprocess.DEVNULL,
                                         stdout = open(self.startup_log, 'w'),
                                         stderr = subprocess.STDOUT)
        self.wait_for_listening(timeout_sec=20)
        return self

    def wait_for_listening(self, timeout_sec: int):
        import socket, time
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=1):
                    return
            except OSError:
                time.sleep(0.2)
        raise RuntimeError(f'Sidecar proxy did not bind on :{self.port} in {timeout_sec}s')

    def healthcheck(self) -> Schema__Health__Check:
        listening = self._port_listening()
        return Schema__Health__Check(check_name='sidecar_proxy',
                                     healthy=listening,
                                     detail=f'port={self.port} listening={listening}')

    def stop(self):
        if self.process:
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: self.process.kill()
```

Invoked from `lambda_entry.py` after config load:

```python
if CONFIG.sidecar_proxy_enabled:
    sidecar = Sidecar__Proxy(port          = CONFIG.sidecar_proxy_port,
                              upstream_url  = CONFIG.mitm_proxy_url,
                              upstream_user = CONFIG.mitm_proxy_user,
                              upstream_pass = CONFIG.mitm_proxy_pass,
                              startup_log   = Path('/tmp/sidecar-startup.log'))
    sidecar.start()
    APP_STATE.sidecar = sidecar
```

### Step 4 — Rewrite `build_proxy_dict`

`Browser__Launcher.build_proxy_dict()` collapses to a one-liner for the sidecar case:

```python
def build_proxy_dict(self, proxy, browser_name) -> Dict[str, Any]:
    # When sidecar proxy is active, the browser always talks to the sidecar
    # over loopback with no auth. Credentials live in the sidecar's upstream config.
    if self.sidecar and self.sidecar.is_running():
        return {'server': f'http://127.0.0.1:{self.sidecar.port}'}

    # Fallback for dev/debug without sidecar (kept for local testing)
    out = {'server': str(proxy.server)}
    if proxy.auth is not None and browser_name != Enum__Browser__Name.CHROMIUM:
        out['username'] = str(proxy.auth.username)
        out['password'] = str(proxy.auth.password)
    if proxy.bypass:
        out['bypass'] = ','.join(str(h) for h in proxy.bypass)
    return out
```

**Note:** `bypass` still passes through, since it's browser-side filtering that controls which hosts skip the proxy entirely. `ignore_https_errors` stays a context-level setting (`new_context(ignore_https_errors=True)`) — required for the TLS cert-unknown retry that Chromium does; see Phase 1.11 notes.

### Step 5 — Remove `Proxy__Auth__Binder.py`

With the sidecar in place, the browser never encounters a 407 challenge. The CDP auth-binding workaround becomes dead code. Delete:

- `sgraph_ai_service_playwright/service/Proxy__Auth__Binder.py`
- Its usage in `Browser__Launcher.launch()` (if any)
- Its tests

Simpler code, fewer moving parts, fewer things to maintain.

### Step 6 — Tests

Unit tests for `Sidecar__Proxy`:
- Starts on fresh port, binds within timeout
- Healthcheck returns healthy when port listening, unhealthy when process dead
- Stop terminates cleanly, port released
- Survives a CONNECT-and-disconnect sequence (use a mocked upstream)

Integration tests (opt-in, require real upstream proxy):
- Chromium navigates example.com through sidecar, returns 200
- Firefox same
- WebKit same
- Invalid upstream creds → sidecar forwards → 407 surfaces cleanly to browser

---

## Trade-offs

### What this buys us

- **Works.** 235ms Chromium nav (Phase 1.11 measurement) vs 30s timeout.
- **Cross-browser uniformity.** Identical path for Chromium/Firefox/WebKit — no per-browser code.
- **Credentials stay server-side.** Browser never sees the upstream password. Reduces attack surface for a compromised browser process.
- **Removes brittle CDP workaround.** `Proxy__Auth__Binder.py` and its subtle event-handler race goes away.
- **Doesn't require fixing the upstream.** Upstream proxy team can address their addon pipeline bug on their timeline; we unblock immediately.

### What it costs

- **+15 MB layer** for the mitmproxy dependency. Acceptable for Lambda.
- **+1 process** at boot, with lifecycle to manage. Sidecar__Proxy class handles that.
- **Startup adds ~2-3 seconds** before first request can be served. Healthcheck gates this.
- **+1 network hop** (browser → sidecar, loopback). Cost ≈ a single-digit ms per request, below measurement noise.
- **Credentials in Lambda env** vs being inlined per-request — this was already the case in practice.

### What we're NOT fixing

- **The upstream proxy's broken retry handling.** A proper fix there would remove the need for the sidecar eventually. Filed separately as a follow-up for the upstream's addon team.
- **The edge case where a user supplies a DIFFERENT proxy in their request** than the configured upstream. Current proposal uses a single, boot-configured upstream. If per-request upstream is needed, future work.

---

## Observability

Sidecar surfaces two signals to the existing `/health` endpoint:

```json
{
  "checks": [
    {"check_name": "sidecar_proxy",
     "healthy": true,
     "detail": "port=8890 listening=true"}
  ]
}
```

Sidecar startup log lands at `/tmp/sidecar-startup.log` (dev) or CloudWatch (Lambda). Each CONNECT and forward is logged by mitmdump — usable for debugging in dev, disabled or sampled in production if log volume is a concern.

---

## Migration path

**Phase A — dev/EC2 rollout**
1. Implement Sidecar__Proxy + rewrite build_proxy_dict
2. Ship to dev branch
3. Run the Phase 1.11 test matrix against the deployed service to confirm
4. Keep Proxy__Auth__Binder in place as fallback until Phase B

**Phase B — Lambda rollout**
1. Validate Lambda startup timing (does the sidecar race the first request?)
2. Validate Firecracker compatibility (mitmdump on Amazon Linux 2023 inside a Lambda runtime)
3. Remove Proxy__Auth__Binder
4. Document new env var contract

**Phase C — cleanup**
1. Delete Proxy__Auth__Binder.py and its tests
2. Delete the Chromium-specific branch in build_proxy_dict
3. Update docs: the proxy-auth story is now "we run a sidecar"

---

## References

- `debug-session/` — full investigation (Phase 1.1 through 1.11)
- `debug-session/phase-1_9__local-mitmproxy/notes.md` — evidence that local mitmproxy works direct
- `debug-session/phase-1_11__upstream-mode/notes.md` — evidence that upstream mode works (this is the design's basis)
- `debug-session/reference/` — laptop PoC source code (the reference implementation)
- `case-study/debrief__2026-04-19__agent-facilitated-debugging.md` — the collaboration pattern that produced this investigation
