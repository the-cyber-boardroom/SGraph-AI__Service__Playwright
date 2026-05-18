---
title: "05 — Eval CLI: step-by-step operational lifecycle"
file: 05__eval-cli-step-by-step.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
parent: README.md
---

# 05 — Eval CLI: step-by-step operational lifecycle

## The idea

Mirror the `setup check` pattern, but for the **runtime / operational
lifecycle of a single slug** rather than the static infrastructure.
Operator runs:

```
sg vault-publish eval run sara-cv
```

…and the CLI executes a fixed sequence of steps, printing each
step's outcome live. Any step can also be run in isolation:

```
sg vault-publish eval step-3-wait-for-running sara-cv
```

The full sequence is the test plan for "the system works end-to-end
for a real slug". Each step in isolation is the test plan for
"this one stage works".

## Naming

`eval` is the proposed name. Alternatives considered:
- `test` — collides with pytest mental model, confuses operators.
- `qa` — implies pre-prod / dry-run, but we're hitting real AWS.
- `lifecycle` — accurate but unwieldy.
- `simulate` — wrong word; we're really doing it, not faking.

**`eval`** is short, distinct from `setup`, and conveys "execute
the operational flow and evaluate each step's outcome".

## The step sequence

Eleven steps; each is one verb with one job. The sequence is
**chronological** — you can't skip step 3 if step 2 hasn't passed.

```
step-1-register         Register a slug with a fresh vault key
step-2-verify-registry  SSM entry present + correct shape
step-3-trigger-wakeup   First HTTP request → Lambda → EC2 start
step-4-wait-for-ec2     Poll until EC2 is RUNNING
step-5-wait-for-workload  Poll until workload port responds (no full health)
step-6-wait-for-healthy   Poll until health probe returns 200
step-7-wait-for-cert    Poll until vault-app serves HTTPS with a valid cert
step-8-verify-direct    Confirm DNS has propagated; hit slug.zone direct
step-9-probe-vault      Authenticate to vault-app, list keys (functional test)
step-10-unpublish       Delete the slug
step-11-verify-gone     Confirm SSM entry, EC2, DNS record all absent
```

Each step takes the slug as argument, returns a typed result
(`Schema__Eval__Step__Result`), and writes its outcome to stdout.
Failure of any step aborts the chain (`eval run`) but doesn't
prevent individual step verbs from being invoked.

---

## Per-step detail

### `step-1-register`

```
$ sg vault-publish eval step-1-register sara-cv-test

  Step 1 / 11 — Register
    → Calling Vault_Publish__Service.register(sara-cv-test, vault-key=…)
    ✓ Registered
      FQDN     : sara-cv-test.aws.sg-labs.app
      Stack    : sara-cv-test
      Elapsed  : 1247 ms
```

Wraps `Vault_Publish__Service.register`. The vault-key is generated
fresh by the eval CLI (random 32 chars) unless `--vault-key <k>` is
passed — so eval is destructive-safe: it never touches an existing
slug unless explicitly told to.

### `step-2-verify-registry`

```
$ sg vault-publish eval step-2-verify-registry sara-cv-test

  Step 2 / 11 — Verify SSM registry
    → Reading SSM path: /sg-compute/vault-publish/slugs/sara-cv-test
    ✓ Found
      stack_name    : sara-cv-test
      fqdn          : sara-cv-test.aws.sg-labs.app
      region        : eu-west-2
      created_at    : 2026-05-18T11:00:00Z
      vault_key     : (redacted, 32 chars)
```

Reads via `Slug__Registry.get`. Pure read.

### `step-3-trigger-wakeup`

```
$ sg vault-publish eval step-3-trigger-wakeup sara-cv-test

  Step 3 / 11 — Trigger wake-up
    → curl -sI https://sara-cv-test.aws.sg-labs.app/
    ✓ Lambda responded
      Status            : 202
      X-Waker-State     : warming
      X-Waker-Action    : started-ec2
      X-Waker-Slug      : sara-cv-test
      X-Waker-Instance  : i-0abc1234
      X-Waker-Elapsed   : 287 ms
```

First HTTP request after register. Confirms Lambda is invoked, slug
resolved, EC2 start triggered. Uses the `X-Waker-*` headers from the
debug-surface brief.

### `step-4-wait-for-ec2`

```
$ sg vault-publish eval step-4-wait-for-ec2 sara-cv-test

  Step 4 / 11 — Wait for EC2 RUNNING
    → Polling describe_instances every 5 s (max 120 s)
    ⌛ 5s    state=pending
    ⌛ 10s   state=pending
    ⌛ 15s   state=pending
    ⌛ 20s   state=pending
    ✓ 25s   state=running
      Public IP  : 1.2.3.4
      Elapsed    : 25 s
```

Direct EC2 API polling, no waker involvement. Bounded with a clear
timeout; fails noisily if EC2 doesn't reach RUNNING.

### `step-5-wait-for-workload`

```
$ sg vault-publish eval step-5-wait-for-workload sara-cv-test

  Step 5 / 11 — Wait for workload port reachable
    → TCP connect 1.2.3.4:8080 every 2 s (max 60 s)
    ⌛ 2s    refused
    ⌛ 4s    refused
    ✓ 6s    connected
      Elapsed : 6 s
```

The "workload port is open" check, separate from full health. This
is the boundary where the broader reverse-proxy (see
[04](04__lambda-reverse-proxy.md)) would kick in.

### `step-6-wait-for-healthy`

```
$ sg vault-publish eval step-6-wait-for-healthy sara-cv-test

  Step 6 / 11 — Wait for workload healthy
    → GET http://1.2.3.4:8080/ui/#!/login every 3 s (max 180 s)
    ⌛ 3s    status=502 (nginx booting)
    ⌛ 6s    status=502
    ⌛ 12s   status=200, 87 ms
    ✓ 12s   healthy
```

Full health probe. Uses the `health_path` from the slug entry
(decoupling brief — see [02](02__decoupling-vault-from-ec2.md)).

### `step-7-wait-for-cert`

```
$ sg vault-publish eval step-7-wait-for-cert sara-cv-test

  Step 7 / 11 — Wait for HTTPS cert
    → HEAD https://sara-cv-test.aws.sg-labs.app/ every 5 s (max 240 s)
    ⌛ 5s    TLS handshake failed (no cert yet)
    ⌛ 10s   TLS handshake failed
    ⌛ 25s   TLS handshake failed
    ⌛ 60s   TLS handshake failed
    ✓ 75s   cert issued
      Issuer    : Let's Encrypt
      Subject   : CN=sara-cv-test.aws.sg-labs.app
      Expires   : 2026-08-16T11:00:00Z
      Elapsed   : 75 s
```

The Let's Encrypt dance. This step is the visible test that the
reverse-proxy + cert flow ([03](03__lets-encrypt-catch-22.md))
works. Today this can fail intermittently due to the DNS race; with
the reverse-proxy fix in place, it should reliably succeed.

### `step-8-verify-direct`

```
$ sg vault-publish eval step-8-verify-direct sara-cv-test

  Step 8 / 11 — Verify direct-EC2 routing
    → dig sara-cv-test.aws.sg-labs.app +short
        1.2.3.4
    ✓ DNS resolves to EC2 IP (not CloudFront)
    → curl -sI https://sara-cv-test.aws.sg-labs.app/
        HTTP/2 200
        (no X-Waker-* headers present)
    ✓ Confirmed: traffic is going direct to EC2, not via Lambda
```

Once per-slug DNS has propagated, requests should bypass Lambda.
Confirms by (a) DNS resolution and (b) absence of `X-Waker-*`
headers in the response.

### `step-9-probe-vault`

```
$ sg vault-publish eval step-9-probe-vault sara-cv-test

  Step 9 / 11 — Functional probe of vault-app
    → POST https://sara-cv-test.aws.sg-labs.app/api/login
        body: {"vault_key": "…"}
    ✓ 200 OK; received session cookie
    → GET https://sara-cv-test.aws.sg-labs.app/api/keys
    ✓ 200 OK; 0 keys (expected for fresh vault)
```

Workload-specific. For vault: log in, list keys, expect empty list.
For other workloads, this step would be different (eg. for the
hypothetical jupyter-publish: open a notebook, run a cell, get
expected output).

This is where the eval CLI becomes workload-aware. The cleanest
abstraction: each workload registers a `probe_function(slug, entry)`
that returns `Schema__Eval__Step__Result`. Default for unknown
workloads: just "GET /, expect 200".

### `step-10-unpublish`

```
$ sg vault-publish eval step-10-unpublish sara-cv-test

  Step 10 / 11 — Unpublish slug
    → Calling Vault_Publish__Service.unpublish(sara-cv-test)
    ✓ Unpublished
      Stack deleted  : sara-cv-test
      SSM cleared    : /sg-compute/vault-publish/slugs/sara-cv-test
      Elapsed        : 2156 ms
```

### `step-11-verify-gone`

```
$ sg vault-publish eval step-11-verify-gone sara-cv-test

  Step 11 / 11 — Verify everything cleaned up
    → SSM lookup            : (not found)        ✓
    → EC2 describe (by tag) : (no instances)     ✓
    → Route 53 record       : (absent)           ✓
    → DNS lookup            : NXDOMAIN           ✓
    → curl https://sara-cv-test.aws.sg-labs.app/
        Status              : 404 (X-Waker-State: not_found)
    ✓ All clean
```

The end-to-end "we left no trace" assertion. Pulls from SSM, EC2,
Route 53, DNS, and a final waker invocation.

---

## The orchestrator

```
sg vault-publish eval run [slug]
```

If `[slug]` is omitted, eval generates one (`eval-{random-6-chars}`)
and uses it. This is the "test on a throwaway slug, then clean it
all up" mode.

```
$ sg vault-publish eval run

  Eval lifecycle — slug: eval-x9k3m2
  ╔═══════════════════════════════════════════════════════════════╗
  ║                                                                ║
  ║   1 / 11   Register                              ✓  1247 ms    ║
  ║   2 / 11   Verify SSM registry                   ✓    23 ms    ║
  ║   3 / 11   Trigger wake-up                       ✓   287 ms    ║
  ║   4 / 11   Wait for EC2 RUNNING                  ✓  25 s       ║
  ║   5 / 11   Wait for workload port                ✓   6 s       ║
  ║   6 / 11   Wait for workload healthy             ✓  12 s       ║
  ║   7 / 11   Wait for HTTPS cert                   ✓  75 s       ║
  ║   8 / 11   Verify direct-EC2 routing             ✓   18 s      ║
  ║   9 / 11   Functional probe of vault-app         ✓   312 ms    ║
  ║  10 / 11   Unpublish slug                        ✓  2156 ms    ║
  ║  11 / 11   Verify everything cleaned up          ✓   847 ms    ║
  ║                                                                ║
  ║   Total: 11 / 11 PASSED in 2 min 22 s                          ║
  ╚═══════════════════════════════════════════════════════════════╝
```

A failure looks like:

```
  ╔═══════════════════════════════════════════════════════════════╗
  ║   …                                                            ║
  ║   6 / 11   Wait for workload healthy             ✗  TIMEOUT    ║
  ║   7 / 11   Wait for HTTPS cert                   ·  SKIPPED    ║
  ║   …                                                            ║
  ║                                                                ║
  ║   FAILED at step 6 / 11                                        ║
  ║                                                                ║
  ║   Step 6 — Wait for workload healthy                           ║
  ║     Last probe : status=502, body=502 Bad Gateway              ║
  ║     Elapsed    : 180 s (timeout exceeded)                      ║
  ║                                                                ║
  ║   For diagnostics:                                             ║
  ║     sg vault-publish status eval-x9k3m2                        ║
  ║     sg vault-publish waker inspect eval-x9k3m2                 ║
  ║                                                                ║
  ║   To clean up the slug:                                        ║
  ║     sg vault-publish eval step-10-unpublish eval-x9k3m2        ║
  ║                                                                ║
  ╚═══════════════════════════════════════════════════════════════╝
```

Failure modes always tell the operator what to run next.

## Flags

| Flag                  | Effect                                                                       |
|-----------------------|------------------------------------------------------------------------------|
| `--slug <s>`          | Use a specific slug (default: generate `eval-{6-chars}`)                     |
| `--keep`              | Skip steps 10–11. Leave the slug for further inspection.                    |
| `--from <step>`       | Skip steps 1..N-1, start at step N. Slug must be passed.                    |
| `--until <step>`      | Stop after step N. Useful for "register but don't probe".                   |
| `--json`              | Emit step results as JSON lines (one per step).                             |
| `--cleanup-on-fail`   | Run step 10 (unpublish) even if an earlier step failed.                     |
| `--timeout-secs <n>`  | Override per-step timeout. Default per step is hard-coded.                  |

## Why this is useful

1. **It's the post-deploy smoke test.** Every Lambda code change
   should be followed by `sg vp eval run`. Catches regressions that
   unit tests miss.
2. **It's the demo script.** Walking someone through how the system
   works = running the steps one at a time and explaining each.
3. **It's the CI integration test.** GH Action job: `sg vp eval run
   --cleanup-on-fail`. Real AWS, real cert dance, real slug
   teardown.
4. **It's the field debug tool.** Operator says "Sara's vault won't
   come up." → run `sg vp eval run --slug sara-cv --from step-4`.
   Finds out exactly which stage breaks.
5. **It validates the decoupling and reverse-proxy work.** Step 5
   (workload port reachable) is meaningful only when decoupled
   probing exists; step 7 (cert) is the regression test for the LE
   catch-22 fix.

## Implementation shape

```
sg_compute_specs/vault_publish/eval/
├── schemas/
│   ├── Enum__Eval__Step__Outcome.py        (PASS / FAIL / SKIP / TIMEOUT)
│   ├── Schema__Eval__Step__Result.py
│   └── Schema__Eval__Run__Report.py
├── service/
│   ├── Eval__Service.py                    (orchestrator: run / from / until)
│   ├── Step_01__Register.py
│   ├── Step_02__Verify_Registry.py
│   ├── ...
│   └── Step_11__Verify_Gone.py
└── cli/
    └── Cli__Eval.py                        (typer app)
```

One step per file. Each step subclasses `Eval__Step__Base` with
`name`, `description`, `expected_duration_seconds`, and a single
`execute(slug) -> Schema__Eval__Step__Result` method.

`Eval__Service.run_all(slug)` walks the registry of steps in order;
each step's result feeds the next (e.g. step 4 returns the IP, step
5 uses it).

## What this doesn't replace

- **Setup check** (the static infra verifier). Setup check is "is
  the launch pad correctly built". Eval is "does a flight succeed
  end-to-end".
- **Unit tests.** Eval hits real AWS, takes minutes, costs cents per
  run. Unit tests catch regressions in code paths in milliseconds.
- **Production monitoring.** Eval is operator-initiated; CW alarms +
  the waker's structured logs are the always-on monitoring.

Eval sits between them: an on-demand, real-AWS, full-lifecycle
exerciser.
