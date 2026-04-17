# Local Validation Spec — Proxy Auth Fix (Bug #1)

**Audience:** Claude dev session working on Bug #1 (proxy auth via CDP Fetch handlers)
**Environment:** Local Python + Playwright — **no Docker required**
**Goal:** Isolate whether the proxy-auth bug is in the service code or in the Lambda environment by reproducing the bug locally, fixing it locally, then confirming the local fix also lands on Lambda.

---

## Why Local Validation

The bug manifests identically in two scenarios:

1. **Service code is wrong** — creds never reach Chromium.
2. **Lambda environment is wrong** — Lambda networking blocks authenticated CONNECT, or the container runtime breaks CDP events.

From outside, both produce the same symptom: navigate hangs at CONNECT, watchdog recycles the container. We can't tell which one it is.

**Running the same service code locally settles it:**

| Local result | Lambda result | Conclusion |
|---|---|---|
| ❌ Fails | ❌ Fails | Bug is in service code. Fix locally, redeploy. |
| ✅ Works | ❌ Fails | Bug is Lambda-environment-specific. Service code is fine; investigate network/runtime. |
| ✅ Works | ✅ Works | Bug is fixed. Ship it. |

The first row is the most likely outcome (based on the credential-ignorance finding — see §"Evidence from QA" below). Local validation collapses debug cycles from "redeploy-and-wait" to "edit-and-retry-in-seconds."

---

## Architectural Reason This Works

The service was designed for dual-mode execution. From `base-image-research.md`:

> When `AWS_LAMBDA_RUNTIME_API` env var is set (Lambda sets this automatically), the [Lambda Web Adapter] activates; otherwise the container runs as a vanilla uvicorn server.

**Translation:** the service is a normal FastAPI app. `AWS_LAMBDA_RUNTIME_API` is Lambda-only; when it's absent, the app runs as a regular HTTP server with no Lambda-specific code path. Nothing about the request handling, Chromium launching, or proxy wiring changes between Lambda and local — only the outer envelope.

That means local reproduction is high-fidelity: whatever the service does wrong, it'll do wrong locally too.

---

## Setup

### Prerequisites

- Python 3.12
- `pip install playwright fastapi uvicorn pytest pytest-timeout requests` (plus whatever the service's `pyproject.toml` lists)
- `playwright install chromium` (downloads the browser — one-time cost, cached in `PLAYWRIGHT_BROWSERS_PATH`)
- Clone of `SGraph-AI__Service__Playwright` on the branch with the proposed fix

### Running the service locally

```bash
cd SGraph-AI__Service__Playwright
export FAST_API__AUTH__API_KEY__NAME=api-key__for__SGraph-AI__App__Send
export FAST_API__AUTH__API_KEY__VALUE=local-dev-key
# Do NOT set AWS_LAMBDA_RUNTIME_API — we want vanilla uvicorn mode
uvicorn sgraph_ai_service_playwright.main:app --host 127.0.0.1 --port 8080
```

Service is now at `http://127.0.0.1:8080`. Same endpoints, same auth, same schemas.

**Sanity check:**
```bash
curl -H "api-key__for__SGraph-AI__App__Send: local-dev-key" http://127.0.0.1:8080/health/info
```
Should return `deployment_target: "local"` (or whatever the non-Lambda value is).

### Standing up a local test proxy

You need a proxy that (a) requires auth and (b) is reachable from the service. `mitmproxy` is the obvious pick — it's Python, no Docker needed.

```bash
pip install mitmproxy
mitmdump --listen-port <PROXY_PORT> --proxyauth <PROXY_USERNAME>:<PROXY_PASSWORD>
```

Now the proxy is at `http://<PROXY_USERNAME>:<PROXY_PASSWORD>@127.0.0.1:<PROXY_PORT>`, requiring Basic auth on every CONNECT.

**Verify the proxy works at the network level** (outside Playwright):
```bash
curl -x http://<PROXY_USERNAME>:<PROXY_PASSWORD>@127.0.0.1:<PROXY_PORT> https://api.ipify.org
# Should return your real IP
curl -x http://wrong-user:wrong-pass@127.0.0.1:<PROXY_PORT> https://api.ipify.org
# Should fail with 407
```

If this works, the proxy is fine and any failure from here is in the service.

---

## The Test Pyramid

Run these in order. Each level catches a different class of bug.

### Level 1 — Pure Playwright (no service, no FastAPI)

Goal: prove the CDP Fetch handler pattern works at all on this machine, with this Playwright version.

```python
# tests/local/test_L1_pure_playwright_cdp.py
from playwright.sync_api import sync_playwright

def test_cdp_auth_works_standalone():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": "http://127.0.0.1:<PROXY_PORT>"},  # no creds in launch args
        )
        ctx  = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        cdp = ctx.new_cdp_session(page)
        cdp.send("Fetch.enable", {"handleAuthRequests": True})
        cdp.on("Fetch.authRequired", lambda p: cdp.send("Fetch.continueWithAuth", {
            "requestId": p["requestId"],
            "authChallengeResponse": {
                "response": "ProvideCredentials",
                "username": "<PROXY_USERNAME>",
                "password": "<PROXY_PASSWORD>",
            },
        }))
        cdp.on("Fetch.requestPaused", lambda p: cdp.send(
            "Fetch.continueRequest", {"requestId": p["requestId"]}))

        page.goto("https://api.ipify.org/?format=json", timeout=10_000)
        content = page.content()
        assert '"ip"' in content, f"Expected IP JSON, got: {content[:200]}"
        browser.close()
```

**If this fails**, the problem is not in the service at all — it's in the CDP pattern, Playwright version, or local proxy setup. Stop and diagnose before going further.

**If this passes**, the pattern works. Now we can check whether the service has wired it up correctly.

### Level 2 — Service code in-process (no HTTP layer)

Goal: exercise the service's session-creation and navigation code paths directly as Python calls, bypassing FastAPI. Fastest feedback loop.

```python
# tests/local/test_L2_service_in_process.py
from sgraph_ai_service_playwright.sessions.Session__Service import Session__Service
from sgraph_ai_service_playwright.schemas.Schema__Browser__Config import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.Schema__Proxy__Config import Schema__Proxy__Config
from sgraph_ai_service_playwright.schemas.Schema__Proxy__Auth__Basic import Schema__Proxy__Auth__Basic  # new in Bug #1 fix

def test_service_creates_proxied_session_and_navigates():
    service = Session__Service()
    browser_config = Schema__Browser__Config(
        browser_name="chromium",
        headless=True,
        proxy=Schema__Proxy__Config(
            server="http://127.0.0.1:<PROXY_PORT>",
            ignore_https_errors=True,
            auth=Schema__Proxy__Auth__Basic(username="<PROXY_USERNAME>", password="<PROXY_PASSWORD>"),
        ),
    )
    session = service.create(browser_config=browser_config, capture_config=...)

    result = service.navigate(session.session_id, url="https://api.ipify.org/?format=json")
    assert result.step_result.status == "passed", result.step_result.error_message

    content = service.get_content(session.session_id).step_result.content
    assert '"ip"' in content

    service.close(session.session_id)
```

**If Level 1 passed but Level 2 fails:** bug is in how the service wires `Schema__Proxy__Config` → Chromium launch + CDP handlers. Debug with print statements or pdb inside the session-creation code. This is where most of the work will happen.

**Likely failure modes and where to look:**

| Symptom | Likely cause |
|---|---|
| `navigate` returns immediately with `status: failed` | CDP handler not registered before first goto |
| `navigate` times out at 5 s | CDP handler registered but not firing (check `Fetch.enable` payload) |
| `create` errors with `authChallengeResponse` not recognised | Passing wrong Playwright method (use `Fetch.continueWithAuth` not `Network.continueInterceptedRequest`) |
| `create` succeeds but *every* request is paused forever | Missing the `Fetch.requestPaused` passthrough handler (critical gotcha — see QA debrief) |

### Level 3 — Full HTTP stack against local uvicorn

Goal: same code path the Lambda uses, just local. Catches bugs in FastAPI routing, schema validation, response shaping.

```python
# tests/local/test_L3_local_http.py
import requests

BASE = "http://127.0.0.1:8080"
HDRS = {"Content-Type": "application/json",
        "api-key__for__SGraph-AI__App__Send": "local-dev-key"}

def test_local_http_proxy_flow():
    r = requests.post(f"{BASE}/session/create", headers=HDRS, json={
        "browser_config": {
            "browser_name": "chromium",
            "headless": True,
            "proxy": {
                "server": "http://127.0.0.1:<PROXY_PORT>",
                "ignore_https_errors": True,
                "auth": {"username": "<PROXY_USERNAME>", "password": "<PROXY_PASSWORD>"},
            },
        },
        "capture_config": {"screenshot": {"enabled": True, "sink": "inline"},
                           "include_execution_result": True},
    })
    r.raise_for_status()
    sid = r.json()["data"]["session_info"]["session_id"]

    try:
        r = requests.post(f"{BASE}/browser/navigate", headers=HDRS, json={
            "session_id": sid,
            "step": {"action": "navigate", "url": "https://api.ipify.org/?format=json"},
        })
        r.raise_for_status()
        sr = r.json()["data"]["step_result"]
        assert sr["status"] == "passed", sr.get("error_message")

        r = requests.post(f"{BASE}/browser/get-content", headers=HDRS, json={
            "session_id": sid,
            "step": {"action": "get_content", "content_format": "text"},
        })
        content = r.json()["data"]["step_result"]["content"]
        assert '"ip"' in content
    finally:
        requests.delete(f"{BASE}/session/close/{sid}", headers=HDRS)
```

**If Level 2 passed but Level 3 fails:** bug is in the HTTP/schema layer — route handlers, request/response schema mapping, auth middleware. Unlikely given the baseline suite already passes for non-proxied sessions, but possible if the `Schema__Proxy__Auth__Basic` type isn't registered with the Type_Safe discovery mechanism.

### Level 4 — Credential-variant probe (same script, local target)

Goal: replicate the credential-ignorance finding locally. If credentials are correctly wired, wrong creds should fail **fast and differently** from right creds.

```python
# tests/local/test_L4_credential_variants.py
CASES = [
    ("correct",       "<PROXY_USERNAME>", "<PROXY_PASSWORD>",  "passed"),
    ("wrong user",    "wrong-user",       "<PROXY_PASSWORD>",  "failed"),
    ("wrong pass",    "<PROXY_USERNAME>", "wrong-pass",        "failed"),
    ("empty creds",   "",                 "",                  "failed"),
]

@pytest.mark.parametrize("label,user,pw,expected", CASES)
def test_credential_variants(label, user, pw, expected):
    # ... create session with user/pw, navigate, assert outcome
    # Key assertion: WRONG creds should fail in < 2 seconds, not stall
    # If all variants take the same time, creds aren't being sent (repro of the Lambda symptom)
```

This is **the regression test for Bug #1**. If it ever fails the "different timings for different creds" check, the wiring has regressed.

### Level 5 — Lambda parity check (after local passes)

Once Levels 1–4 all pass locally with the fix, redeploy to the target environment and re-run the QA proxy harness. Two outcomes:

- **Passes** → Bug #1 is fully fixed. Ship. Update QA findings doc to "✅ resolved."
- **Still fails** → Bug is in the Lambda environment, not the code. Now investigate:
  - Is the upstream proxy reachable from the Lambda's VPC/security group?
  - Does the Lambda execution environment kill CDP websocket connections prematurely?
  - Is there an LWA-specific issue with long-lived Chromium subprocesses that affects CDP event delivery?
  - Does `os._exit(2)` from the watchdog fire before the CDP auth handler completes? (timing race — possible if the handler fires just as the 28 s budget lapses)

---

## Evidence from QA

The QA session against v0.1.22 found that **all credential variants produce identical 5-second timeouts on Lambda**:

```
── correct creds ──      HTTP 200 in 5.52s  status=failed  (Page.goto Timeout)
── wrong username ──     HTTP 200 in 5.49s  status=failed  (Page.goto Timeout)
── wrong password ──     HTTP 200 in 5.50s  status=failed  (Page.goto Timeout)
── both wrong ──         HTTP 200 in 5.47s  status=failed  (Page.goto Timeout)
── empty creds ──        HTTP 200 in 5.48s  status=failed  (Page.goto Timeout)
```

This is a **black-box proof that the creds are not reaching Chromium.** If they were, wrong creds would fail fast (one round-trip to the proxy + 407 + Chromium gives up) while right creds would succeed. All-identical timing means the proxy is receiving unauthenticated CONNECTs regardless of what the API caller supplies.

**Therefore:** the bug is almost certainly in the service's Playwright wiring, and Level 2 above should reproduce it. Level 4 should produce the same all-identical-timings pattern before the fix, and clearly differentiated timings after.

---

## Working Pattern — Why This Matters

This is a pattern worth making standard:

> **When a bug's symptom is reachable both locally and remotely, always reproduce locally first.** A Claude session with local code access can iterate 100× faster than one testing against a deployed Lambda. Local reproduction also answers the "is it the code or the environment" question for free.

The service's dual-mode architecture (uvicorn native / LWA on Lambda) makes this pattern almost trivial. Every future bug report should start by asking "can I repro this with `uvicorn ... :app`?" before touching anything deployed.

---

## Checklist

- [ ] mitmproxy running locally with `--proxyauth`
- [ ] Level 1 passes (pure Playwright + CDP) — baseline sanity
- [ ] Level 2 passes (service in-process) — code-level fix verified
- [ ] Level 3 passes (local HTTP) — stack-level fix verified
- [ ] Level 4 passes (credential variants) — regression test locked in
- [ ] CI integration for Levels 1–4 (pytest + mitmproxy in CI, no Docker needed)
- [ ] Level 5 passes against dev Lambda — final verification
- [ ] QA findings doc updated to reflect Bug #1 closure

---

## Notes for the Dev Session

- The **`Fetch.requestPaused` passthrough handler** is critical. Enabling `Fetch` with `handleAuthRequests: true` pauses *every* request, not just auth-challenged ones. Forgetting the passthrough makes every page hang — different symptom from the current bug, but same severity.
- **Swallow stale `requestId` errors in both handlers.** CDP events fire after navigations abandon requests; calling `Fetch.continueWithAuth` on a stale id throws `Target closed` / `No resolve`. Pattern from the reference `Proxy_Via_Browser.setup_proxy_auth()`:
  ```python
  def on_auth_required(params):
      try:
          cdp.send("Fetch.continueWithAuth", ...)
      except Exception:  # stale interception id
          pass
  ```
- The handler registration must happen **after** the page exists but **before** the first navigation. If you register it per-context at context-creation, it applies to all pages spawned in that context — usually what you want.
- **Don't use `page.on("request")` or `page.route()` for this.** They're higher-level Playwright abstractions that don't integrate with Chromium's proxy auth flow. Only the raw CDP Fetch domain works.
