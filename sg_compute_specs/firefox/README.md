# Firefox Spec

Isolated Firefox browser instance with mitmproxy interception and SSM-backed API key.

## Capabilities

- Full browser automation via Playwright
- HTTP/S traffic interception (mitmproxy)
- Caddy reverse proxy with JWT auth
- Per-node SSM parameter for API key

## Usage

Launch via `POST /api/nodes` with `spec_id=firefox`.
