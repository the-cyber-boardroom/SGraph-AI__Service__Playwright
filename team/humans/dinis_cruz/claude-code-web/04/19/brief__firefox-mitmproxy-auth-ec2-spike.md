# Brief — Firefox + MITMproxy Auth on EC2 (PoC hand-off)

**Status:** Spike in progress. EC2 path proven for Firefox. Firefox + proxy via API **not working** — hypothesis: **MITM proxy basic-auth handshake is not being completed by Firefox** even though Playwright exposes `proxy.auth.username/password` natively.

**Branch:** `claude/general-session-HRsiq`
**Version:** v0.1.31
**Last commit before this brief:** `c6acfdf` (watchdog bump to 120s in EC2 user-data)

---

## 1. What this spike delivered

### 1.1 `scripts/provision_ec2.py` — one-shot EC2 provisioner

Runs locally from a laptop. Spins up a single EC2 instance that pulls the current ECR image and runs the Playwright service as a container on port 8000. Idempotent for IAM + SG; terminates via `--terminate`.

**Architecture:**

```
Laptop (AWS creds)
   │
   │ python scripts/provision_ec2.py --stage dev
   ▼
AWS eu-west-2
 ├── IAM role `sg-playwright-ec2-spike` (EC2 assume-role)
 │    ├─ AmazonEC2ContainerRegistryReadOnly  (docker pull from ECR)
 │    └─ AmazonSSMManagedInstanceCore         (aws ssm start-session)
 ├── Security Group `playwright-ec2-spike`    (:8000 from 0.0.0.0/0)
 └── EC2 instance (AL2023, t3.large, Name=sg-playwright-ec2-spike)
        UserData:
          - dnf install -y docker; systemctl enable --now docker
          - ecr login → docker pull <account>.dkr.ecr.<region>.amazonaws.com/sgraph_ai_service_playwright:latest
          - docker run -d --restart=always -p 8000:8000 \
              -e FAST_API__AUTH__API_KEY__NAME / VALUE
              -e SG_PLAYWRIGHT__DEPLOYMENT_TARGET=container
              -e SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS=120000
              <image>
```

**Key constants** (live in `scripts/provision_ec2.py`):

| Constant | Value | Why |
|---|---|---|
| `EC2__INSTANCE_TYPE` | `t3.large` | 2 vCPU / 8 GB. Firefox + WebKit OOM on smaller |
| `EC2__APP_PORT` | `8000` | Container listens here; SG opens this |
| `SG__NAME` | `playwright-ec2-spike` | NOT `sg-*` — AWS reserves that prefix for SG IDs |
| `IAM__ROLE_NAME` | `sg-playwright-ec2-spike` | Shared between role + instance profile |
| `WATCHDOG_MAX_REQUEST_MS__SPIKE` | `120_000` | Lambda-tuned 28s default killed Firefox + proxy mid-flight |

**Usage:**

```bash
export AWS_DEFAULT_REGION=eu-west-2
export FAST_API__AUTH__API_KEY__NAME=X-API-Key
export FAST_API__AUTH__API_KEY__VALUE=<secret>

python scripts/provision_ec2.py --stage dev          # upsert + launch (~2-3 min to healthy)
python scripts/provision_ec2.py --terminate          # nuke all instances tagged Name=sg-playwright-ec2-spike
```

Returns JSON: `{instance_id, public_ip, base_url, image_uri, ami_id, stage}`.

### 1.2 Same Docker image as Lambda

The EC2 instance pulls **the exact image** GHA builds and pushes to ECR for Lambda deploys. No separate build pipeline. The only difference is the env vars: on EC2 `DEPLOYMENT_TARGET=container` (enables the three-browser capabilities profile); on Lambda `DEPLOYMENT_TARGET=lambda` (chromium-only).

### 1.3 Remote access via SSM

Added `AmazonSSMManagedInstanceCore` to the instance role. Drops you in a shell with zero SSH, no passwords, no port 22 — just:

```bash
aws ssm start-session --target i-<instance-id>
# Inside, user is ssm-user (no docker group); prefix docker commands with sudo
sudo docker logs -f sg-playwright
sudo docker exec -it sg-playwright bash
```

Instance profile credentials are cached at boot, so **policy attachments on an already-running instance require a terminate + reprovision** to take effect.

### 1.4 Code-update story

Three granularity levels (pick the right tool for the change):

| Change type | How | Time |
|---|---|---|
| Python code (step handler, schema, route) | Rebuild image locally → push ECR → `--terminate` + reprovision | ~3-5 min |
| Env var / watchdog tuning | Edit `scripts/provision_ec2.py` → `--terminate` + reprovision | ~2-3 min |
| In-place debug (no rebuild) | SSM in, `sudo docker exec`, edit `/var/task/`, `sudo docker restart sg-playwright` | seconds |

For iterative spike work, option 3 is ideal — the image ships the code under `/var/task/sgraph_ai_service_playwright/`. Edit, restart, test.

---

## 2. What we proved / ruled out

### 2.1 ✅ Lambda Firefox hang is Lambda-specific, not Playwright-specific

Firefox 146 launched cleanly on EC2, fetched `https://www.whatsmybrowser.org` and returned a 200 screenshot. Same image that hangs on Lambda works on EC2. **Root cause of Lambda hang: Firecracker microVM constraints** — restricted `/dev/shm` (177 MB of the 5120 MB memory is actually allocated), IPC model, fork() semantics. Firefox init blocks before the page ever loads.

Consequence: Lambda's capabilities profile should stay `[chromium]` only; multi-browser workloads need an EC2/ECS target. This is a deferred decision (see §5).

### 2.2 ✅ MITM proxy is reachable from the EC2 public IP

From the instance **host**:

```
curl -v -x http://akeia:<pw>@mitmproxy.dev.akeia.ai:8080 https://example.com --insecure
→ 200 OK
```

From **inside the container**:

```
sudo docker exec sg-playwright curl -v -x http://akeia:<pw>@mitmproxy.dev.akeia.ai:8080 https://example.com --insecure
→ 200 OK
```

Both return HTML. The proxy **accepts basic-auth from curl** and tunnels the request. Network path + allowlist + creds are all fine.

### 2.3 ✅ Firefox on EC2 with no proxy works

```
POST /browser/screenshot
{
  "url": "https://www.whatsmybrowser.org",
  "browser_config": { "browser_name": "firefox", "headless": true }
}
→ 200 OK, PNG of "You're using Firefox 146"
```

### 2.4 ❌ Firefox on EC2 **with** the proxy via API fails

```
POST /browser/screenshot
{
  "url": "https://www.whatsmybrowser.org",
  "browser_config": {
    "browser_name": "firefox",
    "proxy": {
      "server": "http://mitmproxy.dev.akeia.ai:8080",
      "auth": {"username": "akeia", "password": "<pw>"},
      "ignore_https_errors": true,
      "bypass": []
    }
  },
  "wait_until": "load",
  "timeout_ms": 90000
}

→ 502
{"detail": "Browser one-shot failed: step[0] action=navigate
  error=Page.goto: Timeout 30000ms exceeded.
  - navigating to \"https://www.whatsmybrowser.org/\", waiting until \"load\""}
```

The Playwright nav hits its internal 30s timeout. No crash, no DNS error, no proxy-auth-rejected message — just hung until nav timeout fires.

Note: `timeout_ms: 90000` in the payload is **not being plumbed through**; Playwright's 30s default is what's timing out. Separate issue worth tracking, but doesn't explain the hang itself (even 60s would hang the same way with a different error boundary).

---

## 3. Current hypothesis

**Firefox is not completing the MITM proxy's basic-auth challenge when the proxy returns `407 Proxy Authentication Required` inside the `CONNECT` tunnel for HTTPS.**

**Evidence supporting this:**
- Playwright's `Browser__Launcher.build_proxy_dict()` currently passes `username` + `password` in `chromium.launch(proxy={...})` ONLY for Firefox/WebKit; Chromium routes via CDP Fetch (QA bug #1 from `Browser__Launcher.py:12-18`).
- For Firefox, Playwright *should* auto-respond to 407 with the credentials, but there are known Playwright + Firefox + authenticated-HTTPS-proxy edge cases (see Playwright GH issues around `proxy.username` for Firefox — historically unreliable).
- No error is raised, the request just hangs — consistent with Firefox waiting for a response that never comes after a failed auth round.

**Evidence against:**
- Chromium has its own CDP workaround for exactly this problem (Proxy__Auth__Binder). Firefox was supposed to NOT need one. If this is the issue, that assumption is wrong.

---

## 4. PoCs to run in the next session

Sequenced roughly by how much they narrow the problem:

### 4.1 Baseline: does Chromium work here?

```
POST /browser/screenshot
browser_name: chromium
same proxy config
```

If Chromium works and Firefox doesn't → Firefox-specific (very likely proxy auth).
If both fail → something about the service's proxy plumbing (less likely given curl works).

### 4.2 Inspect what Playwright is actually doing

SSM into the box, exec into the container, run Firefox manually via Python:

```python
# inside container
python3 -c "
from playwright.sync_api import sync_playwright
pw = sync_playwright().start()
browser = pw.firefox.launch(headless=True, proxy={
    'server': 'http://mitmproxy.dev.akeia.ai:8080',
    'username': 'akeia',
    'password': '<pw>',
})
page = browser.new_page(ignore_https_errors=True)
page.goto('https://example.com', timeout=60000)
print(page.title())
browser.close()
"
```

If this hangs too → Playwright/Firefox-level issue, not service layer.
If this works → the service is dropping `proxy.auth` somewhere between the request schema and `launch()`.

### 4.3 Check the CONNECT exchange

From the host, tcpdump or `mitmproxy -k` on the instance itself against the proxy endpoint — see if a 407 is issued and whether Firefox replies with `Proxy-Authorization`.

Or cheaper: point Firefox at a local squid with basic auth, reproduce without any corporate proxy in the way. If it fails locally too → Playwright/Firefox bug, not `mitmproxy.dev.akeia.ai` specific.

### 4.4 Workaround if the hypothesis holds: CDP-less Firefox auth

Firefox doesn't support CDP, so the Chromium workaround doesn't port over. Options:
- **Pre-inject credentials into a Firefox profile** via `user.js`:
  `network.proxy.credentials-authentication = true` + cached creds. Playwright's Firefox launch supports `firefox_user_prefs`.
- **Use `launch_server` + WebSocket + `route()` interception** to inject `Proxy-Authorization` header manually on every request. Clunky but workable.
- **Switch to unauthenticated proxy**: run a sidecar that holds the creds and forwards to mitmproxy. Cleanest but new infra.

### 4.5 Separately: fix `timeout_ms` plumbing

`timeout_ms: 90000` in the request is getting dropped — Playwright's 30s default is what's firing. Find the call site in `Step__Executor` / `Request__Validator` and trace why a non-zero value isn't reaching `page.goto(timeout=...)`. Small bug, independent of the proxy issue.

---

## 5. Deferred decisions (not this spike)

These are parked until the Firefox+proxy question is resolved:

1. **Revert Lambda capabilities profile to `[chromium]`-only** — the change that enables Firefox+WebKit on Lambda is still live and will 502 anyone who asks for those engines there. Safe to do immediately regardless of the proxy outcome.
2. **Promote EC2 path to ECS Fargate** — if multi-browser is a real requirement. Same image, managed lifecycle, no instance care-and-feeding.
3. **Production debrief** — write `team/claude/debriefs/v0.1.31__ec2-spike.md` once PoCs land; update the reality doc's capabilities table.

---

## 6. Quick reference — commands for the next session

```bash
# Where are we?
git checkout claude/general-session-HRsiq
git log --oneline -10

# Spin up EC2 box
python scripts/provision_ec2.py --stage dev
# → returns {instance_id, public_ip, base_url}

# Remote shell
aws ssm start-session --target i-<id>
sudo docker logs -f sg-playwright
sudo docker exec -it sg-playwright bash

# Tear down
python scripts/provision_ec2.py --terminate

# Full test cycle
curl -X POST "http://<public_ip>:8000/browser/screenshot" \
  -H "$FAST_API__AUTH__API_KEY__NAME: $FAST_API__AUTH__API_KEY__VALUE" \
  -H 'Content-Type: application/json' \
  --max-time 120 \
  -d @payload.json | jq .
```

**Known env vars on the spike container:**
- `FAST_API__AUTH__API_KEY__NAME`, `FAST_API__AUTH__API_KEY__VALUE`
- `SG_PLAYWRIGHT__DEPLOYMENT_TARGET=container`
- `SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS=120000`

Everything else uses the service defaults.

---

## 7. Files touched in this spike (for `git log` / review)

```
scripts/provision_ec2.py                          (new, 170 lines)
tests/unit/scripts/test_provision_ec2.py          (new, 5 tests, all pass)
```

No production code changed. All spike scaffolding; ready to delete or promote once the direction settles.
