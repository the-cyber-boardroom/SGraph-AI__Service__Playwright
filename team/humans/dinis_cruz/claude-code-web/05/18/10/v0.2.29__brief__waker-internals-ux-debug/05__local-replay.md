---
title: "05 — Local replay"
file: 05__local-replay.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 05 — Local replay

The end-to-end test loop that doesn't need AWS. Lets a dev iterate on
the waker state machine, the warming page copy, or the proxy logic
without re-deploying.

## The pitch

Today, to test a change to `Waker__Handler`, you have to:
1. Re-deploy the Lambda (`sg vp bootstrap` or `sg aws lambda <name> deploy`)
2. Wait ~30 s for the update to apply
3. Hit the Function URL
4. Read CloudWatch logs

Total loop time: ~2 minutes. Painful for iteration.

Proposed local replay:
1. `python -m sg_compute_specs.vault_publish.waker.lambda_entry_local`
   (starts a stdlib HTTP server on port 8090, serving the Lambda
   handler with in-memory SSM + EC2 fakes)
2. `curl -H 'Host: sara-cv.aws.sg-labs.app' http://localhost:8090/`
3. Edit, re-run, repeat.

Total loop time: ~5 seconds. Most of that is `curl`.

## The pieces

### `lambda_entry_local.py` (new file)

Wraps the existing `lambda_entry.handler` in a stdlib `http.server`
adapter:

```python
# sg_compute_specs/vault_publish/waker/lambda_entry_local.py
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from sg_compute_specs.vault_publish.waker.lambda_entry import handler


class LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):  self._dispatch()
    def do_POST(self): self._dispatch()

    def _dispatch(self):
        body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        event = {
            'version':        '2.0',
            'rawPath':        self.path.split('?', 1)[0],
            'rawQueryString': self.path.split('?', 1)[1] if '?' in self.path else '',
            'headers':        {k.lower(): v for k, v in self.headers.items()},
            'requestContext': {
                'http':      {'method': self.command, 'path': self.path, 'sourceIp': '127.0.0.1'},
                'requestId': 'local-…',
            },
            'body':            body.decode('utf-8', errors='replace') if body else None,
            'isBase64Encoded': False,
        }
        result = handler(event, None)
        self.send_response(result['statusCode'])
        for k, v in result.get('headers', {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write((result['body'] or '').encode())


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 8090), LocalHandler).serve_forever()
```

No new deps (stdlib only). 30 lines.

### In-memory injection seams

`Waker__Handler` and `Endpoint__Resolver__EC2` already have factory
seams (per the existing code). To run locally with fakes instead of
boto3 calls, we set environment variables that pick the in-memory
implementations:

```
SG_VP_WAKER__USE_IN_MEMORY_RESOLVER=1
SG_VP_WAKER__USE_IN_MEMORY_REGISTRY=1
```

Or, more directly, an `Endpoint__Resolver__In_Memory` class (lives
under `waker/`, alongside `__EC2`) that holds a dict of slug → fake
state. The `lambda_entry_local` script wires this up at startup.

```python
# in lambda_entry_local.py
import os
if os.environ.get('SG_VP_WAKER__USE_IN_MEMORY_RESOLVER'):
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__In_Memory \
        import Endpoint__Resolver__In_Memory
    _fake = Endpoint__Resolver__In_Memory()
    _fake.seed('sara-cv',  state='RUNNING',  vault_url='http://127.0.0.1:9000')
    _fake.seed('alice-cv', state='STOPPED',  instance_id='i-fake-alice')
    _fake.seed('bob-cv',   state='UNKNOWN')
    # Monkey-patch the resolver factory used by Waker__Handler
    from sg_compute_specs.vault_publish.waker import Waker__Handler as _wh
    _wh.Waker__Handler._resolver = lambda self: _fake
```

(Slight grimace at the monkey-patch; cleaner would be to thread the
factory through env-var-aware construction. Trade-off acceptable for
a dev-only entry point.)

### Test slug fixtures

A small CLI helper to seed test slugs into the in-memory store:

```
$ python -m sg_compute_specs.vault_publish.waker.lambda_entry_local --seed
  Seeded:
    sara-cv   RUNNING   http://127.0.0.1:9000
    alice-cv  STOPPED   (will simulate start)
    bob-cv    UNKNOWN
    -         (no slug — 404)

  Listening on http://localhost:8090

$ curl -H 'Host: sara-cv.aws.sg-labs.app' http://localhost:8090/
  (proxies to http://127.0.0.1:9000 — start a real HTTP server there
  for a full loop)

$ curl -H 'Host: alice-cv.aws.sg-labs.app' http://localhost:8090/
  (warming page; in-memory fake transitions STOPPED → PENDING → RUNNING
  over 5 seconds)

$ curl -H 'Host: ghost.aws.sg-labs.app' http://localhost:8090/
  (404 page; unknown slug)
```

The STOPPED → RUNNING simulation is the magic that makes the warming
page UX testable without AWS. Time-based: after `start()` is called,
record a timestamp; resolve checks elapsed and reports
PENDING for 2 s, then RUNNING.

### Hooking into the real proxy locally

To test the proxy path end-to-end:

```
# Terminal 1: a fake vault-app
$ python -m http.server 9000

# Terminal 2: local waker (seeds sara-cv → http://127.0.0.1:9000)
$ python -m sg_compute_specs.vault_publish.waker.lambda_entry_local --seed

# Terminal 3: hit it
$ curl -H 'Host: sara-cv.aws.sg-labs.app' http://localhost:8090/
  (returns the python -m http.server directory listing, proxied
   through Waker__Handler)
```

Tests the full Lambda → Endpoint__Proxy → vault-app chain without
EC2, without Lambda deploy, without CloudFront.

### Replaying captured production events

When `sg vp waker trace` captures a trace to a JSON file (per
[`04__cli-debug-commands.md`](04__cli-debug-commands.md)), the file
includes the full event. Replay locally:

```
$ python -m sg_compute_specs.vault_publish.waker.lambda_entry_local \
         --replay ./waker-trace-sara-cv-20260518-100123.json

  Replaying event from waker-trace-sara-cv-20260518-100123.json
  Original captured at: 2026-05-18T10:01:23.456Z
  
  Result:
    status: 202
    headers:
      x-waker-state: warming
      …
    body size: 1247 bytes
  
  Diff vs original response:
    status:          same (202)
    state:           same (warming)
    instance-id:     differs (was i-0abc1234, now i-fake-alice)
    elapsed-ms:      14 (was 287)
    
  (use --diff-strict to fail on any difference)
```

For "fix the bug, prove the fix" workflows. The diff lets a CI test
assert that a captured production event produces the same logical
output after a code change.

---

## What this unlocks

- **Iterating on warming-page copy.** Edit `Waker__Page.render`,
  re-run, refresh browser. Sub-second loop.
- **Tweaking the state machine.** Add a state, write a test, run
  the local server, send a few curls. No deploy.
- **Reproducing a production incident.** `sg vp waker trace` →
  JSON file → check into the repo → `--replay` runs locally + in CI.
- **Onboarding.** A new contributor can run the waker in 30 seconds
  without an AWS account.

## What it doesn't replace

- Real CloudWatch logs (Lambda runtime quirks, container reuse).
- Real EC2 latency / failure modes.
- Real CloudFront forwarding behaviour (header preservation,
  query-string handling at the edge).

But for ~80% of waker development, local replay is the right loop.
The remaining 20% is what `sg vp waker tail` and `sg vp waker trace`
are for.
