---
title: "03 — Debug surface in the Lambda"
file: 03__debug-surface.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 03 — Debug surface in the Lambda

What the Lambda exposes for diagnosis, in three layers from "always
on" to "operator-gated". CLI consumption is in
[`04__cli-debug-commands.md`](04__cli-debug-commands.md).

---

## Layer 1 — Response headers (always on)

Every response (200, 202, 404, 502) carries a fixed set of
`X-Waker-*` headers. Trivial to add, no infrastructure required,
visible in any browser devtools or curl `-i`.

| Header                  | Example                            | Purpose                                          |
|-------------------------|------------------------------------|--------------------------------------------------|
| `X-Waker-State`         | `proxied`                          | machine-readable state from the state machine    |
| `X-Waker-Slug`          | `sara-cv`                          | the slug Slug__From_Host extracted               |
| `X-Waker-Host`          | `sara-cv.aws.sg-labs.app`          | the Host header the Lambda received              |
| `X-Waker-Instance-Id`   | `i-0abc1234`                       | EC2 instance ID (when applicable)                |
| `X-Waker-Ec2-State`     | `running`                          | EC2 state at resolve time                        |
| `X-Waker-Action`        | `started-ec2` / `proxied` / `none` | what the Lambda did this invocation              |
| `X-Waker-Elapsed-Ms`    | `287`                              | total handler time                               |
| `X-Waker-Request-Id`    | `abcd-1234-…`                      | Lambda request ID; pastes into CloudWatch search |
| `X-Waker-Version`       | `v0.2.29`                          | waker code version                               |

**Values are enums, not free text.** `X-Waker-State` is one of
`{not_found, warming, proxied, error, started}`. `X-Waker-Action` is
one of `{none, started-ec2, proxied, returned-warming, returned-404, returned-502}`.
Operator can grep / parse confidently.

**No secrets.** Slug names are already in the URL (public). Instance
IDs are not secret (they don't grant access). Request IDs are
opaque. No vault keys, no IP addresses (X-Forwarded-For stays out of
the response).

**For the proxied case (state=proxied), waker headers DON'T
overwrite the EC2 headers.** Waker headers go alongside whatever
the vault-app returned. Use `X-Waker-*` namespace so there's no
collision.

```
$ curl -I https://sara-cv.aws.sg-labs.app
HTTP/2 200
content-type: text/html
server: nginx/1.25
x-waker-state: proxied
x-waker-slug: sara-cv
x-waker-instance-id: i-0abc1234
x-waker-ec2-state: running
x-waker-action: proxied
x-waker-elapsed-ms: 287
x-waker-request-id: abcd-1234-…
x-waker-version: v0.2.29
```

curl tells you everything you need. No CLI necessary.

---

## Layer 2 — Structured JSON logs (always on)

Every invocation emits exactly one JSON log line on stdout. Lambda
forwards stdout to CloudWatch Logs. CloudWatch Insights can query
structured JSON natively.

**One log line per invocation. No print scatter. Period.**

```json
{
  "ts":          "2026-05-18T10:01:23.456Z",
  "request_id":  "abcd-1234-…",
  "host":        "sara-cv.aws.sg-labs.app",
  "slug":        "sara-cv",
  "method":      "GET",
  "path":        "/some/path",
  "source_ip":   "1.2.3.4",
  "user_agent":  "Mozilla/5.0 …",
  "state":       "proxied",
  "action":      "proxied",
  "ec2_state":   "running",
  "instance_id": "i-0abc1234",
  "vault_url":   "http://10.0.0.42:8080",
  "status":      200,
  "elapsed_ms":  287,
  "version":     "v0.2.29"
}
```

For error cases, add `error`:

```json
{
  "ts":          "2026-05-18T10:01:23.456Z",
  "request_id":  "wxyz-5678-…",
  "host":        "sara-cv.aws.sg-labs.app",
  "slug":        "sara-cv",
  "state":       "error",
  "action":      "returned-502",
  "ec2_state":   "running",
  "instance_id": "i-0abc1234",
  "status":      502,
  "error":       "ProxyError: connection refused",
  "elapsed_ms":  2034,
  "version":     "v0.2.29"
}
```

**CloudWatch Insights one-liners:**

```
# All requests for a slug, last hour
fields @timestamp, state, action, status, elapsed_ms
| filter slug = 'sara-cv'
| sort @timestamp desc
| limit 50

# All 5xx in the last day
fields @timestamp, slug, status, error, request_id
| filter status >= 500
| stats count() by error

# Slug-by-slug request volume
stats count() by slug

# Cold starts (state=warming after STOPPED)
fields @timestamp, slug, elapsed_ms
| filter action = 'started-ec2'
| stats count() as cold_starts, avg(elapsed_ms) as avg_ms by slug
```

---

## Layer 3 — Debug endpoints (token-gated)

Tightly scoped endpoints that bypass the state machine and return
internal state directly. Gated on `X-Waker-Debug: <token>` header
where `<token>` matches the Lambda env var `WAKER_DEBUG_TOKEN`.

Token-gating means:
- Default operator: no token configured, no debug surface exposed.
- Operator with `WAKER_DEBUG_TOKEN=…` set: knows the token,
  can curl debug endpoints. Token rotates by changing the env var.
- No public exposure: anyone hitting the URL without the token sees
  the normal state machine response.

### `/__waker__/health`

```
$ curl -H "X-Waker-Debug: <token>" https://sara-cv.aws.sg-labs.app/__waker__/health
{
  "ok": true,
  "version": "v0.2.29",
  "lambda_request_id": "abcd-…",
  "cold_start": false,
  "container_age_ms": 124567
}
```

Always-200 if reachable. Lets a probe distinguish "the Lambda is up"
from "the slug resolves but EC2 is sleeping".

### `/__waker__/resolve/{slug}`

```
$ curl -H "X-Waker-Debug: <token>" \
       https://sara-cv.aws.sg-labs.app/__waker__/resolve/sara-cv
{
  "slug": "sara-cv",
  "ssm_present": true,
  "ssm_path": "/sg-compute/vault-publish/slugs/sara-cv",
  "entry": {
    "stack_name": "sara-cv",
    "fqdn": "sara-cv.aws.sg-labs.app",
    "region": "eu-west-2",
    "created_at": "2026-05-16T15:00:00Z"
  },
  "ec2": {
    "instance_id": "i-0abc1234",
    "state": "running",
    "public_ip": "1.2.3.4",
    "private_ip": "10.0.0.42",
    "launched_at": "2026-05-16T15:01:00Z"
  },
  "health_probe": {
    "url": "http://1.2.3.4:8080/ui/#!/login",
    "ok": true,
    "status": 200,
    "elapsed_ms": 43
  }
}
```

This is the "everything you'd want to know about a slug" endpoint.
Combines SSM + EC2 + health probe. Doesn't mutate.

### `/__waker__/registered`

```
$ curl -H "X-Waker-Debug: <token>" https://aws.sg-labs.app/__waker__/registered
{
  "count": 3,
  "slugs": ["alice-cv", "bob-cv", "sara-cv"]
}
```

Lists all registered slugs (no entry contents — just slug names).
Useful for "is the slug I typed actually registered". Reads from
SSM `describe_parameters` under the prefix.

### `/__waker__/event`

```
$ curl -H "X-Waker-Debug: <token>" -H "Host: sara-cv.aws.sg-labs.app" \
       https://<lambda-url>/__waker__/event
{
  "host_seen": "sara-cv.aws.sg-labs.app",
  "slug_derived": "sara-cv",
  "method": "GET",
  "path": "/__waker__/event",
  "headers_count": 7,
  "body_size": 0,
  "source_ip": "1.2.3.4"
}
```

Echoes back what the Lambda saw. The canonical "is the Host header
making it through CloudFront?" debug.

### Security model for the debug endpoints

- Token is a random 32-char string set via `WAKER_DEBUG_TOKEN` env
  var on the Lambda config.
- If env var is not set, debug paths return 404 (indistinguishable
  from a non-existent slug).
- Token compared with `hmac.compare_digest` to avoid timing attacks.
- Endpoints are read-only. None of them mutate state.
- Endpoints work via CloudFront (CF forwards the header) AND via the
  raw Lambda URL.

---

## Why these three layers

- **Headers** — zero-config debug for anyone with curl. Always
  present. Cheapest, highest leverage.
- **Logs** — operator's primary surface. CloudWatch Insights queries
  do real diagnosis. The `request_id` from headers cross-references
  to the log line.
- **Debug endpoints** — for the hard cases where headers and logs
  don't tell you what's happening (e.g. "SSM says X but EC2 says Y").
  Token-gated because they reveal internal state that doesn't belong
  in normal responses.

Operators rarely need layer 3. When they do, layer 3 saves an SSH
session.
