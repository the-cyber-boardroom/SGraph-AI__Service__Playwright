---
title: "01 — Request lifecycle inside the waker"
file: 01__request-lifecycle.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 01 — Request lifecycle inside the waker

A request enters the Lambda. What happens in the ~50–500 ms before
the response leaves? This file is the source of truth for what each
class does and which decision branches exist.

## Outer transport

```
Browser                              CloudFront edge            Lambda Function URL
  │                                       │                            │
  │  GET https://sara-cv.aws.sg-labs.app  │                            │
  │  (DNS resolves to CF — no per-slug    │                            │
  │   A record exists yet because         │                            │
  │   EC2 is stopped)                     │                            │
  ├──────────────────────────────────────▶│                            │
  │                                       │                            │
  │                                       │  Match alias *.aws.sg-…    │
  │                                       │  Cache disabled            │
  │                                       │  Forward Host header       │
  │                                       ├───────────────────────────▶│
  │                                       │                            │
  │                                       │                       Lambda invocation
  │                                       │                       (event/context arrive)
```

What CloudFront forwards (the `event` dict our handler receives):

```json
{
  "version":        "2.0",
  "rawPath":        "/some/path",
  "rawQueryString": "q=1&r=2",
  "headers": {
    "host":             "sara-cv.aws.sg-labs.app",
    "x-forwarded-for":  "1.2.3.4",
    "user-agent":       "Mozilla/5.0 …",
    "accept":           "text/html,*/*"
  },
  "requestContext": {
    "http": {"method": "GET", "path": "/some/path", "sourceIp": "1.2.3.4"},
    "requestId": "abcd-1234-…",
    "time":      "18/May/2026:10:00:00 +0000"
  },
  "body":             null,
  "isBase64Encoded":  false
}
```

Critical: **the `host` header is the real user-facing hostname**
(e.g. `sara-cv.aws.sg-labs.app`), NOT the Lambda Function URL hostname.
CloudFront preserves it. That's how `Slug__From_Host` extracts the slug.

If you hit the Lambda URL directly (`i5dhd…lambda-url.eu-west-2.on.aws`),
the host header is the Lambda URL hostname — `Slug__From_Host` returns
empty, and `Waker__Handler` returns 404. **That's what you saw in
testing.** Correct behaviour.

## Inside the handler — the call graph

```
lambda_entry.handler(event, context)
    │
    │ parse host, method, path, query, body
    │ build Schema__Waker__Request_Context
    │
    ▼
Waker__Handler.handle(ctx)
    │
    ├─ ctx.slug empty? ───────────────────────▶ return _not_found('no slug in host')
    │                                            (404 HTML, no further action)
    │
    │  resolve the slug
    ▼
Endpoint__Resolver__EC2.resolve(slug)
    │
    ├─ Slug__Registry.get(slug)
    │     └─ SSM Parameter Store
    │        /sg-compute/vault-publish/slugs/{slug}
    │        returns JSON entry or None
    │
    ├─ entry is None? ────────────────────────▶ Schema__Endpoint__Resolution(
    │                                              state=UNKNOWN)
    │
    │  entry found — look up the EC2 instance
    │
    ├─ boto3 ec2.describe_instances(Filters=[
    │     tag:StackName=<entry.stack_name>,
    │     tag:StackType='vault-app',
    │     state in (running, stopped, pending, stopping)])
    │
    └─▶ Schema__Endpoint__Resolution(
            slug, instance_id, public_ip,
            vault_url='http://{ip}:8080',
            state=RUNNING/STOPPED/PENDING/STOPPING/UNKNOWN,
            region)

    │
    │  state machine in Waker__Handler.handle:
    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  state == UNKNOWN                                                    │
│     └─ return _not_found(slug)                                       │
│                                                                       │
│  state == STOPPED                                                    │
│     ├─ if instance_id: Endpoint__Resolver__EC2.start(instance_id)   │
│     │     └─ boto3 ec2.start_instances([instance_id])                │
│     └─ return _warming(slug, 202)                                    │
│                                                                       │
│  state == PENDING or STOPPING                                        │
│     └─ return _warming(slug, 202)        (don't re-call start)       │
│                                                                       │
│  state == RUNNING and vault_url                                      │
│     ├─ self._health_ok(vault_url)?       (urllib3 GET /ui/#!/login)  │
│     │                                                                 │
│     ├─ healthy ───────────▶ Endpoint__Proxy.proxy(...)               │
│     │     │                  └─ urllib3 forward request to EC2:8080  │
│     │     └─ return proxied response (status, headers, body)         │
│     │                                                                 │
│     └─ not healthy ──────▶ return _warming(slug, 200)                │
│                                                                       │
│  fallback ───────────────▶ return _warming(slug, 202)                │
└──────────────────────────────────────────────────────────────────────┘
    │
    ▼
lambda_entry.handler — translate result dict to Lambda response:
    {
      'statusCode': result['status_code'],
      'headers':    result['headers']        (minus Content-Length),
      'body':       result['body'].decode()  (or str passthrough),
      'isBase64Encoded': False
    }
```

## The state machine, written out

| Resolved EC2 state | Vault URL? | Health? | Action taken                  | Response                  |
|--------------------|------------|---------|-------------------------------|---------------------------|
| no slug in Host    | —          | —       | none                          | 404 HTML                  |
| UNKNOWN            | —          | —       | none                          | 404 HTML                  |
| STOPPED            | —          | —       | EC2 StartInstances            | 202 warming HTML          |
| PENDING            | —          | —       | none (already starting)       | 202 warming HTML          |
| STOPPING           | —          | —       | none (race; treat as warm-up) | 202 warming HTML          |
| RUNNING            | yes        | yes     | proxy request to EC2          | 200 + EC2 response        |
| RUNNING            | yes        | no      | none (EC2 booting up)         | 200 warming HTML          |
| RUNNING            | no         | —       | none (no IP yet?)             | 202 warming HTML          |
| (other)            | —          | —       | none (defensive fallback)     | 202 warming HTML          |

Note: **the per-slug Route 53 A record is NOT created by the Lambda.**
That happens on `sg vault-app start` — the auto-DNS logic on the
container side, when the EC2 boots, registers the per-slug record.
Once registered, subsequent DNS queries skip CloudFront and the Lambda
is out of the data path entirely (the "warm path" of the spec).

## What the Lambda DOES NOT do

- **Doesn't write to SSM.** Only reads. Registry writes happen via
  `sg vp register` from the operator's machine.
- **Doesn't update Route 53.** The per-slug record is managed by the
  vault-app on the EC2 side (auto-DNS on start).
- **Doesn't talk to CloudFront.** Only receives requests from it.
- **Doesn't cache.** Stateless — every request re-resolves the slug.
  (The next iteration could cache slug → instance-id for a few seconds
  to reduce SSM costs; out of scope here.)
- **Doesn't authenticate.** Function URL is AuthType=NONE. Any request
  to the Function URL or to CloudFront is processed. Authentication is
  the vault-app's job (it serves the vault UI which authenticates).

## Timing budgets (typical, on warm Lambda container)

| Step                                         | Typical | Worst case |
|----------------------------------------------|---------|------------|
| Lambda runtime cold start                    | —       | 1500 ms    |
| Parse event + build context                  | 1 ms    | 5 ms       |
| SSM `get_parameter`                          | 30 ms   | 200 ms     |
| EC2 `describe_instances`                     | 80 ms   | 500 ms     |
| EC2 `start_instances` (when STOPPED)         | 100 ms  | 800 ms     |
| Health probe (`urllib3 GET /ui/#!/login`)    | 50 ms   | 2000 ms (timeout 2 s) |
| Proxy request (`urllib3 GET vault page`)     | 150 ms  | 30000 ms (timeout 30 s) |
| Total (STOPPED → return warming page)        | ~250 ms | ~1500 ms   |
| Total (RUNNING + healthy → proxied response) | ~300 ms | ~32000 ms  |

EC2 cold start (instance boots, vault-app stack comes up) is the long
pole — typically 30–90 seconds from `start_instances` to vault-app
serving HTTP. The user sees the warming page auto-refresh during this
window.

## Failure modes worth noting

1. **SSM parameter exists but EC2 was terminated manually.**
   `_find_instance` returns None → state=UNKNOWN → 404. Operator
   sees "slug not found" even though the slug IS registered. Need
   a debug path to distinguish "no SSM entry" from "SSM entry but no
   EC2".

2. **EC2 running but vault-app stack crashed.** State=RUNNING,
   vault_url present, but health probe fails or proxy gets 502.
   Today: returns 200 warming page forever. User sees an infinitely
   warming page. Need: timeout / fallback to a "vault-app unhealthy"
   page after N retries.

3. **Public IP changed between `resolve` and `proxy`.** EC2 just
   booted; describe returned a stale state. Proxy targets the old IP
   and gets a connection error. Today: returns 502 via the proxy's
   exception handler. Recovery: next request re-resolves and finds
   the new IP. Acceptable.

4. **Lambda cold start hides the warming.** First-ever request to a
   new slug: Lambda cold-starts (1.5 s) + SSM lookup + EC2 start +
   warming page render = ~2 s before the browser sees the spinner.
   This is acceptable; warming page renders cleanly within budget.

5. **Two clients hit STOPPED state concurrently.** Both call
   `start_instances`. AWS de-duplicates internally (idempotent). No
   problem — both get the warming page.

All of these need to be observable. That's the rest of this brief.
