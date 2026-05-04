# Chained Proxy Setup — agent-mitmproxy → Upstream Proxy

**Date:** 2026-04-21  
**Status:** Working (with manual workarounds — see Open Items for native implementation)  
**Context:** EC2 Docker stack running the SGraph Playwright service

---

## Architecture

The full traffic chain once upstream proxy mode is enabled:

```
Client
  │
  ▼
Playwright service (port 8000)
  │  spawns Chromium with proxy=http://agent-mitmproxy:8080
  ▼
agent-mitmproxy sidecar (port 8080)   ← our mitmproxy instance
  │  intercepts + inspects all traffic
  │  forwards via --mode upstream:<url>
  │  injects upstream auth automatically (--set upstream_auth)
  ▼
Upstream proxy (external mitmproxy instance)
  │  does its own TLS interception
  │  adds its own response headers (x-proxy-service, x-proxy-status, etc.)
  ▼
Target (google.com, bbc.co.uk, etc.)
```

Both mitmproxy instances (our sidecar and the upstream) are doing TLS interception, so there are two layers of forged certs in play:

- **Sidecar CA** — presented to Chromium (trusted via `IGNORE_HTTPS_ERRORS=true`)
- **Upstream CA** — presented to our sidecar when it connects to the upstream

---

## Configuration

### docker-compose.yml — agent-mitmproxy service

```yaml
agent-mitmproxy:
  environment:
    AGENT_MITMPROXY__UPSTREAM_URL:  'http://<upstream-proxy-host>:<port>'
    AGENT_MITMPROXY__UPSTREAM_USER: '<username>'
    AGENT_MITMPROXY__UPSTREAM_PASS: '<password>'
```

When `UPSTREAM_URL` is set, the entrypoint builds:
```
mitmweb --mode upstream:<url> --set upstream_auth=<user>:<pass> ...
```

When empty (default), the sidecar runs in direct mode — no upstream forwarding.

---

## The Problem — Certificate Chain

### What we expected
```
sidecar → upstream proxy → target
```

### What actually happens (two mitmproxy instances chained)

1. Sidecar sends `CONNECT target.com:443` to upstream proxy
2. Upstream proxy responds `200 Connection established`
3. Upstream proxy presents its **own forged cert** for `target.com` to the sidecar
4. Sidecar tries to verify that cert against its system CA store
5. **Fails** — the upstream proxy's CA is not trusted by the sidecar

Error seen:
```
502 Bad Gateway
Certificate verify failed: unable to get local issuer certificate
```

This is different from the Chromium→sidecar cert trust, which is handled by `IGNORE_HTTPS_ERRORS=true`. That setting only affects Chromium, not mitmproxy itself.

---

## Experiments Run

### 1. Direct curl from container to upstream proxy (bypassing sidecar)
```bash
docker exec sg-playwright-agent-mitmproxy-1 curl -v \
  -x http://<user>:<pass>@<upstream-proxy>:8080 \
  https://www.example.com
```
**Result:** ✅ Worked. Confirmed upstream proxy reachable and auth credentials correct.

**Lesson:** This bypasses the sidecar entirely. Success here only proves upstream reachability, not the full chain.

### 2. Curl through sidecar (the real chain)
```bash
docker exec sg-playwright-agent-mitmproxy-1 curl -v \
  -x http://agent-mitmproxy:8080 \
  --cacert /tmp/sidecar-ca.pem \
  https://www.example.com
```
**Result:** ❌ `502 Bad Gateway — Certificate verify failed: unable to get local issuer certificate`

**Lesson:** The sidecar itself is failing cert verification against the upstream proxy's forged cert.

### 3. Install upstream CA into sidecar trust store
```bash
docker exec sg-playwright-agent-mitmproxy-1 curl -s \
  -x http://<user>:<pass>@<upstream-proxy>:8080 \
  http://mitm.it/cert/pem -o /tmp/upstream-ca.pem

docker exec sg-playwright-agent-mitmproxy-1 \
  cp /tmp/upstream-ca.pem /usr/local/share/ca-certificates/upstream-proxy-ca.crt
docker exec sg-playwright-agent-mitmproxy-1 update-ca-certificates
```
**Result:** ❌ `0 added, 0 removed` — did not take. The sidecar mitmweb process did not reload its trust store.

### 4. Add --ssl-insecure to mitmweb (workaround — confirmed working)

The entrypoint writes the mitmweb command to `/tmp/run_mitmweb.sh` at container start. Edit that file and restart mitmweb:

```bash
# Edit the generated command
docker exec sg-playwright-agent-mitmproxy-1 bash -c \
  'sed -i "s|exec mitmweb|exec mitmweb --ssl-insecure|" /tmp/run_mitmweb.sh'

# Verify
docker exec sg-playwright-agent-mitmproxy-1 cat /tmp/run_mitmweb.sh

# Find mitmweb PID (no ps available in this container)
grep -rl mitmweb /proc/*/cmdline 2>/dev/null | grep -v self | grep -v thread | while read f; do
  pid=$(echo $f | cut -d/ -f3)
  cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
  echo "$pid: $cmdline"
done

# Kill it — supervisord autorestart=true will relaunch with the updated script
kill <mitmweb-pid>
```

**Result:** ✅ Full chain working. Verified with:

```bash
curl -v --max-time 10 \
  -x http://agent-mitmproxy:8080 \
  --cacert /tmp/sidecar-ca.pem \
  https://www.example.com
```

Key indicators of success:
- `SSL certificate verify ok`
- `issuer: CN=mitmproxy; O=mitmproxy` — sidecar's CA, interception active
- `x-proxy-service: mgraph-proxy` — upstream proxy headers present
- `x-agent-mitmproxy-elapsed-ms` — our sidecar's addon ran
- HTTP 200 with page content

**Note:** This fix is lost on container restart. See Open Items.

---

## Cookie Injection Experiment

### Goal
Inject `mitm-mode=inject` as a cookie on all GET requests passing through the sidecar, so the upstream proxy can identify intercepted traffic.

### What was tried

The correct file to edit is `/app/agent_mitmproxy/addons/default_interceptor.py` — **not** `/app/current_interceptor.py`. The addon registry imports from the package directly:

```python
# /app/agent_mitmproxy/addons/addon_registry.py
from agent_mitmproxy.addons.default_interceptor import addons as interceptor_addons
from agent_mitmproxy.addons.audit_log_addon      import addons as audit_addons
addons = [*interceptor_addons, *audit_addons]
```

Editing `current_interceptor.py` has no effect — it is not loaded by the addon registry.

After editing `default_interceptor.py` and restarting mitmweb, cookie injection worked — confirmed via `https://httpbin.org/cookies`:

```json
{
  "cookies": {
    "mitm-mode": "inject"
  }
}
```

### The problem — InvalidBodyLengthError

When cookie injection was active, heavier pages started returning:

```
502 Bad Gateway
HTTP/2 protocol error: InvalidBodyLengthError: Expected 37002 bytes, received 7089
```

This is an HTTP/2 framing issue between our sidecar and the upstream proxy. The upstream returns a compressed response with a `Content-Length` that doesn't match after mitmproxy processes it. This happened on pages with larger responses (not on simple endpoints like httpbin).

Adding `flow.response.decode()` in the response handler did not resolve it.

### Decision

Cookie injection via the interceptor causes HTTP/2 body length corruption on heavier pages. The decision was to:

1. **Revert the interceptor** to the original (no cookie injection)
2. **Implement cookie injection browser-side** via JavaScript instead — cleaner, no mitmproxy response handling involved

The `InvalidBodyLengthError` is also worth raising with the upstream proxy team (akeia) — it may be a bug in how their proxy sets `Content-Length` on compressed HTTP/2 responses.

### Interceptor file after revert (original state)

```python
import secrets
import time
from datetime                                       import datetime, timezone
from agent_mitmproxy.consts.version                 import version__agent_mitmproxy

HEADER__REQUEST_ID   = 'X-Agent-Mitmproxy-Request-Id'
HEADER__REQUEST_TS   = 'X-Agent-Mitmproxy-Request-Ts'
HEADER__ELAPSED_MS   = 'X-Agent-Mitmproxy-Elapsed-Ms'
HEADER__VERSION      = 'X-Agent-Mitmproxy-Version'
METADATA__REQUEST_ID = 'agent_mitmproxy_request_id'

class Default_Interceptor:
    def request(self, flow):
        request_id                          = secrets.token_hex(6)
        flow.metadata[METADATA__REQUEST_ID] = request_id
        flow.request.headers[HEADER__REQUEST_ID] = request_id
        flow.request.headers[HEADER__REQUEST_TS] = datetime.now(timezone.utc).isoformat()

    def response(self, flow):
        request_id = flow.metadata.get(METADATA__REQUEST_ID, '')
        flow.response.headers[HEADER__REQUEST_ID] = request_id
        flow.response.headers[HEADER__VERSION    ] = str(version__agent_mitmproxy)
        start_ts = getattr(flow.request, 'timestamp_start', None)
        if start_ts is not None:
            elapsed_ms = int((time.time() - start_ts) * 1000)
            flow.response.headers[HEADER__ELAPSED_MS] = str(elapsed_ms)

addons = [Default_Interceptor()]
```

---

## Open Items for Native Implementation

### 1. Add `AGENT_MITMPROXY__SSL_INSECURE` env var (required for chained mitmproxy)

The entrypoint script (`/app/entrypoint.sh`) should support:

```yaml
AGENT_MITMPROXY__SSL_INSECURE: 'true'
```

Change in `entrypoint.sh`:

```sh
if [ "${AGENT_MITMPROXY__SSL_INSECURE:-}" = "true" ]; then
    MITMWEB_CMD="${MITMWEB_CMD} --ssl-insecure"
fi
```

Add to `docker-compose.yml` agent-mitmproxy environment section:

```yaml
AGENT_MITMPROXY__SSL_INSECURE: 'true'
```

Without this, every container restart requires the manual `/tmp/run_mitmweb.sh` edit + mitmweb kill cycle.

### 2. Browser-side cookie injection

Rather than injecting cookies in the mitmproxy interceptor (which causes HTTP/2 body length issues), inject via JavaScript after navigation in the Playwright service:

```python
await page.evaluate("document.cookie = 'mitm-mode=inject; path=/'")
```

This avoids any mitmproxy response handling and works cleanly for all page sizes.

### 3. InvalidBodyLengthError — raise with upstream proxy team

When mitmproxy modifies requests passing through to the upstream proxy, some responses come back with mismatched `Content-Length` vs actual body size under HTTP/2. This causes:

```
HTTP/2 protocol error: InvalidBodyLengthError: Expected N bytes, received M
```

This needs investigation on the upstream proxy side — it may be setting `Content-Length` based on the compressed size but delivering decompressed content (or vice versa) after mitmproxy touches the request.

### 4. Persist upstream CA cert in the image (alternative to --ssl-insecure)

If the upstream proxy has a stable CA cert, bake it into the image at build time:

```dockerfile
COPY upstream-proxy-ca.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
```

This is more secure than `--ssl-insecure` (verifies the upstream cert rather than skipping verification) but requires the upstream CA to be stable and known at build time.

---

## Useful Debugging Commands

```bash
# Check current sidecar env vars
docker inspect sg-playwright-agent-mitmproxy-1 | \
  python3 -c "import json,sys; c=json.load(sys.stdin)[0]; [print(e) for e in c['Config']['Env']]"

# Check the generated mitmweb command
docker exec sg-playwright-agent-mitmproxy-1 cat /tmp/run_mitmweb.sh

# Find mitmweb PID (no ps in this container)
grep -rl mitmweb /proc/*/cmdline 2>/dev/null | grep -v self | grep -v thread | while read f; do
  pid=$(echo $f | cut -d/ -f3)
  cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
  echo "$pid: $cmdline"
done

# Kill mitmweb (supervisord will auto-restart it)
kill <pid>

# Fetch sidecar CA cert
docker exec sg-playwright-agent-mitmproxy-1 curl -s \
  -x http://agent-mitmproxy:8080 \
  http://mitm.it/cert/pem -o /tmp/sidecar-ca.pem

# Test direct to upstream (bypasses sidecar — explicit auth required)
docker exec sg-playwright-agent-mitmproxy-1 curl -v --max-time 10 \
  -x http://<user>:<pass>@<upstream-proxy>:8080 \
  https://www.example.com

# Test through sidecar (the real chain — sidecar injects auth)
docker exec sg-playwright-agent-mitmproxy-1 curl -v --max-time 10 \
  -x http://agent-mitmproxy:8080 \
  --cacert /tmp/sidecar-ca.pem \
  https://www.example.com

# Tail sidecar logs
docker logs -f sg-playwright-agent-mitmproxy-1 2>&1
```
