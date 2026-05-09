# Driving `jlesage/firefox` remotely with WebDriver BiDi

A complete pattern for remotely controlling the Firefox running inside
[`jlesage/firefox`](https://github.com/jlesage/docker-firefox) — without
Selenium, Playwright, or geckodriver. A human can watch and interact with
the same browser via noVNC while scripts drive it programmatically.

The full implementation is in [`sg-firefox-bidi-pack.zip`](sg-firefox-bidi-pack.zip).

## What problem this solves

`jlesage/firefox` runs Firefox inside a virtual desktop and exposes it via
noVNC for human interaction. It's perfect for "I want a Firefox in a
container that I can SSH into and use." But the moment you want to drive
that Firefox from a script — navigate URLs, run JavaScript, capture HTML,
intercept network traffic — every common path has a sharp edge:

- **Playwright** can't connect to vanilla Firefox. It needs its own patched
  build launched by `playwright launchServer`. Using it means giving up the
  human-visible browser for a separate one.
- **Selenium + geckodriver** works, but adds machinery and the ergonomics
  push you toward starting a *new* Firefox rather than attaching to the
  existing one.
- **CDP (`--remote-debugging-port`)** is dead in modern Firefox. As of 145
  it serves WebDriver BiDi, not Chrome DevTools Protocol.
- **Marionette directly** binds loopback only with no escape hatch, and
  the Python ecosystem for talking to it is thin.

The catch with all of these is the same: Firefox's automation protocols
hardcode binding to `127.0.0.1`, and the `--marionette-host` /
`--remote-debugging-address` flags that look like they should help are
silently ignored.

## What we built

A small stack that augments `jlesage/firefox` with a `socat` sidecar to
expose Firefox's loopback-bound BiDi WebSocket on the docker network, plus
a Python client and CLI to drive it.

```
┌─── firefox container ─────────────────┐    ┌── your sidecar ──┐
│  Firefox (loopback only):             │    │  python script   │
│    127.0.0.1:9222 ← BiDi WebSocket    │    │  using           │
│                                       │    │  firefox_bidi.py │
│  socat sidecar (shared netns):        │ ←─ │  ws://firefox    │
│    0.0.0.0:9223 → 127.0.0.1:9222      │    │   :9223/session  │
│                                       │    │                  │
│  noVNC (5800) ← human view            │    └──────────────────┘
└───────────────────────────────────────┘
```

The whole thing fits in ~30KB of files: a `docker-compose.yml`, a 5MB
socat container, ~300 lines of Python for the BiDi client, a Typer CLI,
and a few helper scripts.

## What's in the pack

```
sg-firefox-bidi-pack/
├── README.md                          ← entry point + quick start
├── SECURITY.md                        ← operational security notes
├── CHANGELOG.md
├── docker/
│   ├── docker-compose.yml             ← firefox + bidi-relay + mitmproxy
│   └── Dockerfile.firefox-cli         ← image for the CLI
├── python/
│   ├── firefox_bidi.py                ← async BiDi client class
│   └── firefox_cli.py                 ← Typer CLI wrapping the client
├── scripts/
│   ├── install.sh                     ← one-shot bootstrap
│   ├── restart.sh                     ← safe firefox+relay restart
│   └── ffcli.sh                       ← shell helper to invoke the CLI
└── docs/
    ├── ARCHITECTURE.md                ← how the pieces fit together
    ├── USAGE.md                       ← CLI + Python usage reference
    ├── TROUBLESHOOTING.md             ← failure modes and fixes
    └── BACKGROUND.md                  ← decision record (dead ends documented)
```

## Quick start

```sh
unzip sg-firefox-bidi-pack.zip
cd sg-firefox-bidi-pack
./scripts/install.sh
source scripts/ffcli.sh

ffcli open https://example.com
ffcli title
ffcli screenshot -o /tmp/shot.png
ffcli eval "document.querySelectorAll('a').length"
```

If you keep `https://<host>:443` (the noVNC view) open in another browser
tab while running these, you'll see the same Firefox respond to each
command in real time.

## Why direct WebDriver BiDi

The pack talks BiDi over WebSocket directly — no Selenium, no Playwright,
no geckodriver in the loop. That choice is worth a brief defence:

**Pro: minimal dependency surface.** ~300 lines of Python plus the
`websockets` library. No browser-version-coupled tooling, no patched
Firefox binary, no Selenium grid. This is the "boring" part of the design.

**Pro: future-proof protocol.** WebDriver BiDi is the
[W3C-standardised cross-browser successor](https://w3c.github.io/webdriver-bidi/)
to CDP and Marionette. Mozilla has committed to it as their long-term
automation protocol. Selenium 4 and Puppeteer both support it.

**Pro: shared driver/observer.** You're driving the same Firefox process
the human sees in noVNC. Captchas, MFA, weird login flows can be done
manually by a human and scripts continue afterwards.

**Con: lower-level than Playwright/Selenium APIs.** No `find_element`, no
`WebDriverWait`. You write JS expressions via `eval()` for those. This is
fine for the use cases that motivated the pack; it'd be tedious if you
were building a complex test suite.

**Con: single session at a time.** Firefox's BiDi only allows one active
session per browser. The Python client holds one long-lived session;
parallelism means running multiple Firefox containers.

The full reasoning, including all the dead ends we tried, is in
`docs/BACKGROUND.md` inside the pack.

## Two non-obvious tricks worth knowing

### 1. Network namespace sharing for the relay

The `bidi-relay` container uses `network_mode: "service:firefox"` so
socat sees Firefox's `127.0.0.1` as its own loopback. This avoids
modifying the jlesage image or installing socat into a running
container.

```yaml
bidi-relay:
  image: alpine/socat
  network_mode: "service:firefox"
  command: TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222
```

Trade-off: when Firefox restarts, the namespace is recreated and the
relay's listener silently dies (the container shows as "Up" but its
socat is bound to a dead namespace). The included `scripts/restart.sh`
handles this by always recreating both together.

### 2. Host header workaround

Firefox's `--remote-allow-hosts` does exact string matching on the full
`Host:` header value, and silently rejects allowlist entries containing
colons. So no flag value gets `Host: firefox:9223` accepted.

The Python client opens the TCP socket itself, then tells the WebSocket
library a different URL whose Host header (`localhost:9222`) Firefox
does accept:

```python
sock = socket.create_connection((firefox_ip, 9223))
async with websockets.connect("ws://localhost:9222/session", sock=sock):
    ...
```

This is a one-time quirk in `FirefoxBiDi.connect()`; the rest of the API
hides it.

## Caveats

- **No auth on the BiDi port.** Don't expose it to untrusted networks.
  Bind to `127.0.0.1` on the host or keep it on a private docker network.
- **`navigator.webdriver` is `true`.** Anti-bot fingerprinting will detect
  this. Same limitation as Selenium without extensions.
- **One BiDi session at a time.** Use the Python client class long-lived
  rather than reconnecting per task. CLI invocations end their session
  cleanly so you can chain them.
- **mitmproxy as part of the stack** decrypts TLS via an installed CA
  cert in the Firefox profile. Treat `/opt/sg-firefox/mitmproxy-data/`
  as sensitive.

See `SECURITY.md` and `docs/TROUBLESHOOTING.md` inside the pack for more.

## Provenance

This started as an investigation into why Playwright wouldn't connect to
`jlesage/firefox`. It turned into a tour of every Firefox automation
protocol and ended up with the simplest thing that works. The dead ends
along the way (Marionette, CDP, Playwright server modes, geckodriver
`--connect-existing`, `selenium/standalone-firefox`) are documented in
`docs/BACKGROUND.md` so future readers don't waste time re-discovering
why the obvious paths don't fit.

## Licence

The pack itself is released under the same licence as this repository.
External components (`jlesage/firefox`, `alpine/socat`, `mitmproxy`) are
under their respective upstream licences.
