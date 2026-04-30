# Firefox Stack — Ops Briefing

_Generated: 2026-04-30_

---

## What the stack is

A single EC2 instance running two Docker containers via docker-compose:

| Container   | Image                    | Port | Purpose                              |
|-------------|--------------------------|------|--------------------------------------|
| `firefox`   | `jlesage/firefox`        | 5800 | Firefox + noVNC web viewer (HTTPS)   |
| `mitmproxy` | `mitmproxy/mitmproxy`    | 8081 | HTTP/HTTPS proxy + flow inspector UI |

Firefox is pre-configured (via `user.js`) to proxy all traffic through the mitmproxy sidecar. The mitmproxy CA cert is installed into Firefox's own NSS certificate store (`cert9.db`) at boot using `certutil`, so HTTPS is intercepted transparently with no cert warnings.

---

## Boot modes

### Full boot (from AL2023 AMI)

`sp firefox create [--interceptor <name>] [--wait]`

What happens in order:

1. EC2 instance starts
2. `dnf install docker nss-tools` — ~2 min
3. docker-compose plugin downloaded from GitHub — ~30s
4. `docker compose pull` (firefox + mitmproxy images) — ~2–3 min
5. mitmproxy starts, generates CA cert
6. `certutil -A` installs the CA cert into the Firefox NSS profile
7. `user.js` written to the profile (proxy config + behaviour prefs)
8. Firefox container starts
9. noVNC server ready on port 5800

**Total: ~5–7 minutes** from `create` to browser access.

### Fast boot (from Firefox AMI)

`sp firefox create-from-ami --from-ami <ami-id> [--wait]`

The AMI already has: docker installed, images pulled, CA cert baked into the profile. Fast user-data only restarts docker and runs `docker compose up -d`.

**Total: ~30–60 seconds** from `create-from-ami` to browser access.

---

## Accessing the stack

```
sp firefox info <stack-name>
```

| Endpoint    | URL                                | Notes                          |
|-------------|------------------------------------|--------------------------------|
| Browser UI  | `https://<ip>:5800/`               | Accept self-signed cert        |
| Credentials | `user` / `<password-from-create>`  | Shown once at create time      |
| mitmweb UI  | `http://<ip>:8081/`                | All HTTP flows visible here    |

The security group restricts both ports to your IP at create time.

---

## First-load black screen — observed behaviour

When you first open `https://<ip>:5800/` in your browser you will see a **black screen** for 10–30 seconds before Firefox appears. This is normal:

1. **noVNC JS loading** (~500 KB served from the container) — the browser tab spinner stays active while assets load
2. **X11 desktop** — noVNC connects and shows the raw X display background (black by default); Firefox has not rendered yet
3. **Firefox cold start** — Firefox itself takes 5–15 seconds to start (profile init, extension loading)
4. **Firefox update check** — on every startup Firefox phones home to check for browser and extension updates; this can add 10–30 seconds before the first window renders, depending on outbound latency

The tiny square cursor visible bottom-right confirms noVNC is connected and waiting for Firefox to draw.

**If the screen stays black for more than ~60 seconds** after it appears, Firefox likely crashed. SSH to the instance and check `docker logs firefox`.

---

## Firefox update check — mitigation

Firefox's update check runs on every startup (not just the first time), including on AMI-booted instances. It can delay the first render by 10–30 seconds.

Disabled via `user.js`:

```javascript
user_pref("app.update.auto",          false);
user_pref("app.update.enabled",       false);
user_pref("extensions.update.enabled", false);
```

These are now included in `USER_JS_TEMPLATE` inside `Firefox__User_Data__Builder`, so all new instances (both full-boot and AMI-boot) will have them. Existing instances need a new stack or a manual `user.js` edit.

---

## Interceptors

mitmproxy is configured with a single active script at `/opt/sg-firefox/interceptors/active.py`. mitmproxy watches the file with inotify and reloads it within ~1 second on change — no restart needed.

### Switching interceptors on a running instance

```bash
sp firefox set-interceptor <stack-name> --interceptor <name>
# or
sp firefox set-interceptor <stack-name> --interceptor-script ./my_script.py
```

Uses AWS SSM `send_command` to write the new script — no SSH needed, no restart needed.

### Built-in examples

| Name              | Description                                           |
|-------------------|-------------------------------------------------------|
| `header_logger`   | Print all request headers to mitmproxy log            |
| `header_injector` | Inject `X-Sg-Firefox-Marker` into every request       |
| `flow_recorder`   | Log method, URL and status for every response         |
| `response_logger` | Log HTTP status + method + URL for every response     |
| `cookie_logger`   | Print Set-Cookie headers for every response           |
| `block_trackers`  | Block common ad/tracker domains with 204              |
| `request_timer`   | Time each request and print elapsed ms + status       |
| `add_cors`        | Add CORS headers to every response                    |

### Writing a custom interceptor

Any valid mitmproxy addon script works. Minimum shape:

```python
def response(flow):
    if 'text/html' in flow.response.headers.get('content-type', ''):
        text = flow.response.get_text()
        flow.response.set_text(text.replace('foo', 'bar'))
```

Script source is validated (no C0 control chars), base64-encoded for safe SSM transmission, and written atomically. Unicode and emoji are allowed.

---

## AMI workflow

```bash
# 1. Bake AMI from a running stack
sp firefox ami create <stack-name>

# 2. Wait until available (~5-10 min)
sp firefox ami wait <ami-id>

# 3. List available AMIs
sp firefox ami list

# 4. Launch fast instance from AMI
sp firefox create-from-ami --from-ami <ami-id> --wait
```

---

## Useful one-liners

```bash
# Create, wait until browser is reachable
sp firefox create --wait

# Check health (shows firefox-ok + mitmweb-ok rows)
sp firefox health <stack-name>

# Live update interceptor without restarting
sp firefox set-interceptor <stack-name> --interceptor-script ./intercept.py

# Shut down
sp firefox delete <stack-name>
```
