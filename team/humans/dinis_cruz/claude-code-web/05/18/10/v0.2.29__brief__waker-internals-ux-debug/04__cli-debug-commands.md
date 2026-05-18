---
title: "04 — CLI debug commands"
file: 04__cli-debug-commands.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 04 — CLI debug commands

What the operator types when something's wrong. Builds on the debug
surface from [`03__debug-surface.md`](03__debug-surface.md).

The goal: every diagnostic an operator might want should be a single
`sg vp waker <verb>` command. No console clicking. No copy-pasting
ARNs.

---

## Proposed verb tree

```
sg vault-publish waker tail            # stream CloudWatch logs in real time
sg vault-publish waker invoke          # invoke the Lambda with a synthetic event
sg vault-publish waker inspect <slug>  # full diagnostic of one slug
sg vault-publish waker trace <slug>    # invoke + collect headers + log line in one pass
sg vault-publish waker fake-event      # print a sample Lambda event for piping into local replay
sg vault-publish waker info            # show Lambda function info (URL, version, code size, etc.)
sg vault-publish waker logs --since 1h # one-shot log dump with filtering
sg vault-publish waker query <expr>    # run a CloudWatch Insights query
```

All verbs read-only. None mutate the Lambda code or AWS state.

---

## `sg vp waker tail`

Stream CloudWatch Logs from the waker log group, formatted for humans.

```
$ sg vp waker tail
[10:01:23.456] sara-cv  proxied        200  287ms  i-0abc1234  abcd-…
[10:01:24.012] alice-cv warming        202   89ms  i-0def5678  efgh-…   (started-ec2)
[10:01:24.500] sara-cv  proxied        200  201ms  i-0abc1234  ijkl-…
[10:01:25.100] bob-cv   not_found      404   12ms  -           mnop-…
[10:01:25.300] sara-cv  error          502 2034ms  i-0abc1234  qrst-…   ProxyError: connection refused
```

Implementation: wraps `boto3.logs.filter_log_events` with
`--follow=True` semantics + a pretty-formatter for our JSON log lines.

Flags:
- `--slug sara-cv`       filter to one slug
- `--state error`        filter to one state
- `--since 5m`           start point (default: now)
- `--json`               raw JSON instead of pretty table

---

## `sg vp waker invoke`

Invoke the Lambda directly with a synthetic Function URL event.

```
$ sg vp waker invoke --host sara-cv.aws.sg-labs.app --method GET --path /
  Invoking sg-compute-vault-publish-waker…
  
  Response:
    status: 202
    headers:
      x-waker-state: warming
      x-waker-slug: sara-cv
      x-waker-instance-id: i-0abc1234
      x-waker-ec2-state: stopped
      x-waker-action: started-ec2
      x-waker-elapsed-ms: 287
      x-waker-request-id: abcd-…
    body size: 1247 bytes (truncated; pass --full to see body)
  
  CloudWatch log line:
    {"ts":"2026-05-18T10:01:23.456Z","slug":"sara-cv","state":"warming",…}
```

Flags:
- `--host`               sets the Host header (required)
- `--method`             HTTP method (default GET)
- `--path`               request path (default /)
- `--header k=v`         add an extra header (repeatable)
- `--body @file.json`    request body
- `--full`               print full response body
- `--debug-token <tok>`  add the `X-Waker-Debug` header

Wraps `boto3.lambda.invoke` with a hand-built v2.0 Lambda Function
URL event. Faster than curl-through-CF, exercises the same code path.

---

## `sg vp waker inspect <slug>`

The "everything you'd want to know" command. Combines SSM lookup +
EC2 describe + health probe + recent log scan.

```
$ sg vp waker inspect sara-cv

  Slug: sara-cv

  Registry (SSM):
    Path        /sg-compute/vault-publish/slugs/sara-cv
    Stack       sara-cv
    FQDN        sara-cv.aws.sg-labs.app
    Region      eu-west-2
    Created     2026-05-16T15:00:00Z

  EC2 instance:
    InstanceId  i-0abc1234
    State       running
    PublicIP    1.2.3.4
    PrivateIP   10.0.0.42
    Launched    2026-05-16T15:01:00Z
    Tags        StackName=sara-cv, StackType=vault-app, sg:slug=sara-cv

  Route 53 per-slug A record:
    Name        sara-cv.aws.sg-labs.app
    Type        A
    TTL         60
    Value       1.2.3.4                                       ✓ matches public IP

  Vault-app health probe:
    URL         http://1.2.3.4:8080/ui/#!/login
    Status      200
    Elapsed     43ms                                          ✓ healthy

  Recent waker invocations (last 1h):
    24 requests
      18 proxied      (avg 287ms)
       2 warming      (avg 102ms; action=started-ec2)
       4 not_found    (you might want to look — host: foo.aws.sg-labs.app)

  Overall: HEALTHY ✓
```

Tells the operator everything in one shot. If anything is wrong
(stale DNS, unhealthy probe, error rate), it's called out inline.

Flags:
- `--json`               machine-readable output
- `--no-logs`            skip the recent invocations scan (faster)

---

## `sg vp waker trace <slug>`

Invoke + collect every layer of debug info in one pass. Useful for
"reproduce a bug and capture everything".

```
$ sg vp waker trace sara-cv
  
  Invoking with Host: sara-cv.aws.sg-labs.app, GET /
  
  ┌─ Response ────────────────────────────────────────────────────┐
  │ Status:        202                                              │
  │ Body size:     1247 bytes                                       │
  │ Headers:                                                        │
  │   x-waker-state:        warming                                 │
  │   x-waker-slug:         sara-cv                                 │
  │   x-waker-action:       started-ec2                             │
  │   x-waker-elapsed-ms:   287                                     │
  │   x-waker-request-id:   abcd-1234-…                             │
  └────────────────────────────────────────────────────────────────┘
  
  ┌─ CloudWatch log line (request_id=abcd-…) ───────────────────────┐
  │ {                                                                │
  │   "ts": "2026-05-18T10:01:23.456Z",                              │
  │   "slug": "sara-cv",                                             │
  │   "state": "warming",                                            │
  │   "action": "started-ec2",                                       │
  │   "ec2_state": "stopped",                                        │
  │   "instance_id": "i-0abc1234",                                   │
  │   ...                                                            │
  │ }                                                                │
  └────────────────────────────────────────────────────────────────┘
  
  ┌─ EC2 state (live) ──────────────────────────────────────────────┐
  │ State:           pending  (just transitioned from stopped)        │
  │ Estimated ready: ~60s                                            │
  └────────────────────────────────────────────────────────────────┘
  
  Saved trace to: ./waker-trace-sara-cv-20260518-100123.json
```

The saved JSON is reproducible — `sg vp waker replay <file>` re-runs
the same synthetic event for "did the fix work" verification.

---

## `sg vp waker fake-event [--slug <slug>]`

Print a sample Lambda Function URL v2.0 event to stdout. Pipe to
`jq`, save to a file, or feed into `sg vp waker invoke --body @-`.

```
$ sg vp waker fake-event --slug sara-cv --method GET --path /api/test
{
  "version": "2.0",
  "rawPath": "/api/test",
  "headers": {
    "host": "sara-cv.aws.sg-labs.app",
    "user-agent": "sg-vp-waker-fake-event/0.1",
    "x-forwarded-for": "127.0.0.1"
  },
  "requestContext": {
    "http": {"method": "GET", "path": "/api/test", "sourceIp": "127.0.0.1"},
    "requestId": "fake-event-…",
    "time": "18/May/2026:10:01:23 +0000"
  },
  "body": null,
  "isBase64Encoded": false
}
```

Useful for local replay (see [`05__local-replay.md`](05__local-replay.md)).

---

## `sg vp waker info`

Pretty-print the Lambda function configuration. No invocation, just
metadata.

```
$ sg vp waker info

  Lambda function: sg-compute-vault-publish-waker

  ARN              arn:aws:lambda:eu-west-2:745506449035:function:sg-compute-vault-publish-waker
  Region           eu-west-2
  Runtime          python3.12
  Handler          sg_compute_specs.vault_publish.waker.lambda_entry.handler
  Memory           512 MB
  Timeout          60 s
  Code SHA256      AbCdEf…
  Last modified    2026-05-18T08:23:14.000Z
  Role             arn:aws:iam::745506449035:role/sg-compute-vault-publish-waker-role
  Layers           (none)
  Env vars         (none set)
  Function URL     https://i5dhd…lambda-url.eu-west-2.on.aws/
  Auth type        NONE
  Reserved concur. (unreserved)
```

Wraps `Lambda__AWS__Client.info()` + `get_function_url()`.

---

## `sg vp waker logs [flags]`

One-shot log dump (vs `tail`'s streaming). Same pretty-printer.

```
$ sg vp waker logs --since 30m --slug sara-cv --state error
[09:34:12] sara-cv  error  502  2034ms  i-0abc  ProxyError: connection refused
[09:37:55] sara-cv  error  502  1987ms  i-0abc  ProxyError: connection refused
```

Flags: `--since`, `--until`, `--slug`, `--state`, `--limit`, `--json`.

---

## `sg vp waker query <insights-expression>`

Pass-through to CloudWatch Insights with a sensible default time
range (last 1h) and pretty-printed table output.

```
$ sg vp waker query 'stats count() by slug, state'

  slug       state         count
  sara-cv    proxied         247
  sara-cv    warming           3
  sara-cv    error             1
  alice-cv   proxied         158
  alice-cv   not_found         4
  bob-cv     not_found        12
```

Flag: `--last 24h`, `--json`.

---

## Mapping commands to incident types

| The operator says…                                 | Verb to run                                       |
|----------------------------------------------------|---------------------------------------------------|
| "Sara's vault is down"                             | `sg vp waker inspect sara-cv`                     |
| "Lots of 502s lately"                              | `sg vp waker query 'filter status >= 500 \| stats count() by slug, error'` |
| "Did the new deploy work?"                         | `sg vp waker info` + `sg vp waker trace sara-cv` |
| "I changed an SSM entry; did the Lambda see it?"   | `sg vp waker invoke --host sara-cv.aws.sg-labs.app` |
| "Watch what's happening live"                      | `sg vp waker tail`                                |
| "Reproduce yesterday's bug"                        | `sg vp waker replay ./waker-trace-….json`         |
| "What slugs are even registered?"                  | `sg vp list` (existing) or curl `/__waker__/registered` |
| "Is the Lambda even reachable?"                    | `curl -H "X-Waker-Debug: <tok>" https://…/__waker__/health` |

The CLI shouldn't need to grow further once these verbs exist.
Most incidents fit one of those eight rows.
