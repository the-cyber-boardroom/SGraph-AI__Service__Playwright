<!-- ═══════════════════════════════════════════════════════════════════════════
  Docker Hub overview — diniscruz/sg-playwright
  Paste verbatim into Docker Hub: Manage Repository → Overview.
  Docker Hub renders GitHub-flavoured Markdown. Keep this file in sync.
═══════════════════════════════════════════════════════════════════════════ -->

# sg-playwright

**Browser automation as an HTTP service.** A self-contained Docker image that exposes Playwright + headless Chromium as a typed REST API — multi-step sequences, batched probes, stateful session handles, screenshots, PDFs, DOM/a11y extraction, console + network forensics, and Prometheus metrics.

Designed for AI agents, scrapers, and ops scripts that need to drive a real browser without holding one. Same image runs on AWS EC2, AWS Lambda Container Image, GCP Cloud Run, your laptop, and CI.

* **Image**: `diniscruz/sg-playwright`
* **Multi-arch**: `linux/amd64` + `linux/arm64`
* **Base**: `mcr.microsoft.com/playwright/python:v1.58.0-noble`
* **Runtime**: Python 3.12 · FastAPI · sync Playwright · AWS Lambda Web Adapter

---

## Quick start

```bash
docker run -d --name sgpw \
  --shm-size=2g \
  -p 8000:8000 \
  -e FAST_API__AUTH__API_KEY__NAME=X-API-Key \
  -e FAST_API__AUTH__API_KEY__VALUE=my-secret \
  diniscruz/sg-playwright:latest

# wait a couple of seconds for the service to come up, then:
curl -sf -H "X-API-Key: my-secret" http://localhost:8000/health/info
```

Take a screenshot of any URL:

```bash
curl -sH "X-API-Key: my-secret" -H "Content-Type: application/json" \
  -X POST http://localhost:8000/screenshot \
  -d '{"url":"https://example.com","format":"png"}'
```

`--shm-size=2g` is non-negotiable — Chromium uses `/dev/shm` for renderer IPC and Docker's 64 MB default starves it after a handful of requests.

---

## What's in the API

### 24 step verbs

```
navigate · click · fill · press · select · hover · scroll
wait · wait_for · screenshot · evaluate · dispatch_event
set_viewport · video_start · video_stop
get_content · get_url · get_text · get_html · get_dom_tree
get_a11y_tree · get_pdf · get_console_tail · get_network_failures
```

### Top-level routes

| Route | Purpose |
|---|---|
| `POST /sequence/execute` | Linear multi-step script |
| `POST /inspect` | **Snapshot once, probe many** — one navigate + settle, then a named bag of read-only probes |
| `POST /session/{open,act,probe,close}` | Stateful session — amortise navigate + decrypt across many calls |
| `POST /browser/{navigate,click,fill,get-content,get-url,screenshot}` | One-shot endpoints |
| `POST /screenshot`, `/screenshot/batch` | Render PNG or HTML, one request |
| `GET /health/{info,status,capabilities}` | Service info + readiness |
| `GET /metrics` | Prometheus text-exposition format |
| `GET /docs` | Live Swagger UI |

### `wait_for` predicates (top wins)

```
function · network_idle_ms · text · selector(+selector_gone/visible/attached) · url_pattern · state
```

### Capture sinks

`inline` (base64 in response), `local_file` (disk inside container). Vault / S3 sinks scaffolded; landing in a fast-follow image.

---

## Authentication

| Path | Header | Why |
|---|---|---|
| Direct (this image, mapped port) | `X-API-Key: <value>` | API-key middleware checks the header you configured via `FAST_API__AUTH__API_KEY__*` env vars |
| Behind the SGraph `/pw` vault proxy | `x-sgraph-access-token: <token>` | The proxy strips the inbound token and injects `X-API-Key` upstream. Sending `X-API-Key` to the proxy gets `401`. |

---

## Configuration (env vars)

| Var | Default | Effect |
|---|---|---|
| `FAST_API__AUTH__API_KEY__NAME` | `X-API-Key` | Header name the API-key middleware reads |
| `FAST_API__AUTH__API_KEY__VALUE` | `(none)` | Required; the secret value |
| `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` | unset | When set, browser contexts skip TLS validation. For EC2 stacks with an `agent_mitmproxy` sidecar doing TLS interception. |
| `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` | unset | Boot-time outbound proxy for the launched browser |
| `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` | bundled | Override the Chromium path (rarely needed) |
| `SG_PLAYWRIGHT__ROOT_PATH` | unset | When behind a reverse proxy that strips a prefix, set it here so `/docs` + `/openapi.json` emit correct URLs |

---

## Deploy targets

* **AWS EC2** — `docker run` directly, or via the `sg va create --with-playwright` workflow
* **AWS Lambda Container Image** — already wired (AWS Lambda Web Adapter included). Note: the `/session/*` stateful feature does NOT work on Lambda because the container can sleep and lose held pages.
* **GCP Cloud Run / Cloud Functions Gen2** — works out of the box; same caveat for `/session/*`
* **Local Docker** — full functionality, ideal for dev + CI

---

## Source + docs

* **Source code**: [the-cyber-boardroom/SGraph-AI__Service__Playwright](https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright)
* **Claude session guide (paste-ready)**: [`library/guides/v0.2.54__playwright-api-via-pw__claude-session-guide.md`](https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright/blob/dev/library/guides/v0.2.54__playwright-api-via-pw__claude-session-guide.md)
* **Skill pack for AI agents**: [`library/skills/use-sg-playwright/SKILL.md`](https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright/blob/dev/library/skills/use-sg-playwright/SKILL.md)
* **Live Swagger** (once running): `http://localhost:8000/docs`

---

## Tags

* `latest` — most recent dev build (multi-arch)
* `vN.N.N` — immutable, version-pinned (multi-arch)

Each release is gated on:
* 4 600+ unit tests
* A live integration suite that drives the actual built image against real public targets before tagging — a broken image never gets `:latest`.

---

Built by [Dinis Cruz](https://github.com/DinisCruz). Issues + PRs welcome on the [GitHub repo](https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright/issues).
