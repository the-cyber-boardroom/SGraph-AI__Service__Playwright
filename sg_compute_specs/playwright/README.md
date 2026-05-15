# sg-playwright — Browser Automation API

A FastAPI service for browser automation: declarative step sequences,
screenshots, navigation, content extraction. Ships as a single Docker image
that runs identically on a laptop, in CI, on EC2, or in Fargate.

**Image:** [`diniscruz/sg-playwright`](https://hub.docker.com/r/diniscruz/sg-playwright)
on Docker Hub — multi-arch (`linux/amd64` + `linux/arm64`).

---

## Quick start

```bash
# Pull the image (or a pinned version: diniscruz/sg-playwright:v0.1.162)
docker pull diniscruz/sg-playwright:latest

# Run it — the API-key value is required; pick any non-trivial string
docker run -d --name sg-playwright \
  -p 8000:8000 \
  -e FAST_API__AUTH__API_KEY__VALUE=my-secret-key \
  diniscruz/sg-playwright:latest

# Check it's up (health is open — no key needed)
curl http://localhost:8000/health/status
```

The service listens on **port 8000**.

### Apple Silicon

The image is multi-arch, so on an Apple Silicon Mac `docker pull` /
`docker run` automatically use the **native `arm64`** variant — no flags, no
emulation.

If you ever need to force the `amd64` variant (e.g. to reproduce an x86-only
issue), Docker Desktop can emulate it:

```bash
docker run --platform linux/amd64 ... diniscruz/sg-playwright:latest
```

Note that emulated Chromium is noticeably slower — only use this when you
specifically need x86 behaviour.

---

## Authentication

Every endpoint except `/health/*` requires an API key. The container reads
the expected value from `FAST_API__AUTH__API_KEY__VALUE`; callers send it in
the **`x-api-key`** header.

```bash
curl http://localhost:8000/sequence/execute \
  -H "x-api-key: my-secret-key" \
  -H "content-type: application/json" \
  -d '{ ... }'
```

| Env var                          | Purpose                                   | Default     |
|-----------------------------------|-------------------------------------------|-------------|
| `FAST_API__AUTH__API_KEY__VALUE`  | Expected API-key value (**required**)     | —           |
| `FAST_API__AUTH__API_KEY__NAME`   | Header name callers must use              | `x-api-key` |
| `PORT`                            | Port the service binds                    | `8000`      |
| `SG_PLAYWRIGHT__DEFAULT_PROXY_URL`| Route all browser traffic through a proxy | unset       |
| `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` | Trust forged certs (set with a TLS-intercepting proxy) | unset |

---

## Invoking the API

Interactive docs are served at **`http://localhost:8000/docs`** (Swagger UI).

### Health (no key required)

```bash
curl http://localhost:8000/health/status         # liveness
curl http://localhost:8000/health/info           # service + version info
curl http://localhost:8000/health/capabilities   # what this deployment can do
```

### Navigate to a page

```bash
curl http://localhost:8000/browser/navigate \
  -H "x-api-key: my-secret-key" \
  -H "content-type: application/json" \
  -d '{"url": "https://sgraph.ai"}'
```

Other one-shot `/browser/*` endpoints: `click`, `fill`, `get-content`,
`get-url`, `screenshot`. Each launches a fresh Chromium, runs the action,
and tears down.

### Take a screenshot

```bash
curl http://localhost:8000/screenshot \
  -H "x-api-key: my-secret-key" \
  -H "content-type: application/json" \
  -d '{"url": "https://sgraph.ai", "full_page": false, "format": "png"}' \
  --output screenshot.png
```

### Run a multi-step sequence

`POST /sequence/execute` runs a declarative list of steps in one fresh
browser context. Each step has an `action` discriminator.

```bash
curl http://localhost:8000/sequence/execute \
  -H "x-api-key: my-secret-key" \
  -H "content-type: application/json" \
  -d '{
        "steps": [
          {"action": "navigate",   "url": "https://sgraph.ai"},
          {"action": "screenshot", "full_page": true},
          {"action": "get_content"}
        ]
      }'
```

---

## docker-compose

```yaml
services:
  sg-playwright:
    image: diniscruz/sg-playwright:latest
    ports:
      - "8000:8000"
    environment:
      FAST_API__AUTH__API_KEY__VALUE: my-secret-key
```

```bash
docker compose up -d
```

---

## Running with a capturing proxy

To route browser traffic through a TLS-intercepting proxy (e.g. mitmproxy)
for capture or rewriting, set two env vars at container start:

```bash
docker run -d --name sg-playwright \
  -p 8000:8000 \
  -e FAST_API__AUTH__API_KEY__VALUE=my-secret-key \
  -e SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy:8080 \
  -e SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=1 \
  diniscruz/sg-playwright:latest
```

The proxy is boot-time infrastructure — it applies to every request, not
per-call. For a one-command paired-proxy stack, the `sp playwright` spec
CLI provides `--with-mitmproxy` (see the spec design doc).

---

## Building locally

```bash
# from the repo root
docker build -f sg_compute_specs/playwright/Dockerfile \
             -t sg-playwright:dev .
docker run -p 8000:8000 -e FAST_API__AUTH__API_KEY__VALUE=dev sg-playwright:dev
```

The image is published automatically by `.github/workflows/ci-pipeline.yml`
on every push to `dev` / `main` that touches `sg_compute_specs/playwright/**`
or `sg_compute/**`.
</content>
