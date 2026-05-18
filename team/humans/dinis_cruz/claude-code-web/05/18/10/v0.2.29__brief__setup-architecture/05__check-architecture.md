---
title: "05 — Check architecture"
file: 05__check-architecture.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 05 — Check architecture

## The headline verb

```
sg vault-publish setup check
```

…reads the live state of every setup resource in the target
(account, region) and prints a single report. No mutations. Returns
exit code 0 if everything is `OK`, non-zero if anything is `MISSING`
or `DRIFT`.

This is the verb that operators run before deployment, after an
incident, during quarterly reviews, in CI.

## What it does

```
Setup__Service.check_all() → Schema__Setup__Report
    ├─ Setup__ACM.check()             → Schema__Setup__ACM__Report
    ├─ Setup__IAM.check()             → Schema__Setup__IAM__Report
    ├─ Setup__Lambda.check()          → Schema__Setup__Lambda__Report
    ├─ Setup__Function_URL.check()    → Schema__Setup__Function_URL__Report
    ├─ Setup__CloudFront.check()      → Schema__Setup__CF__Report
    └─ Setup__DNS.check()             → Schema__Setup__DNS__Report
```

Each area's `check` returns its own typed report. `Setup__Service`
aggregates them into a parent report and computes an overall state.

## The unified report schema

```python
class Schema__Setup__Report(Type_Safe):
    target_region    : str
    target_account   : str
    zone             : str
    overall_state    : Enum__Setup__State                # OK if all areas OK; else DRIFT/ERROR
    elapsed_ms       : int
    
    acm              : Schema__Setup__ACM__Report
    iam              : Schema__Setup__IAM__Report
    lambda_          : Schema__Setup__Lambda__Report
    function_url     : Schema__Setup__Function_URL__Report
    cloudfront       : Schema__Setup__CF__Report
    dns              : Schema__Setup__DNS__Report
    
    issues_total     : int                                # sum across all areas
    actions_needed   : List__Setup__Action                # "run X to fix Y"
```

## The state enum

```python
class Enum__Setup__State(str, Enum):
    OK       = 'ok'         # resource present and matches expected config
    MISSING  = 'missing'    # resource not present at all
    DRIFT    = 'drift'      # present but doesn't match expected config
    ERROR    = 'error'      # couldn't read state (permission denied, network, etc.)
    UNKNOWN  = 'unknown'    # check not yet run
```

`OK` → no action. `MISSING` → run `setup * create`. `DRIFT` → run
`setup * update`. `ERROR` → operator investigation needed.

## Human output

The default CLI output is a colour-coded table that prints in seconds:

```
$ sg vault-publish setup check

  Setup check — account 745506449035, region eu-west-2, zone aws.sg-labs.app

  ┌────────────────┬──────────┬──────────────────────────────────────────────────────────┐
  │ Area           │ State    │ Notes                                                    │
  ├────────────────┼──────────┼──────────────────────────────────────────────────────────┤
  │ ACM            │ ✓ OK     │ arn:aws:acm:us-east-1:…:certificate/abc (covers *.aws.…) │
  │ IAM            │ ⚠ DRIFT  │ inline policy missing ssm:GetParameter statement         │
  │ Lambda         │ ✓ OK     │ sg-compute-vault-publish-waker — Python3.12, 512 MB      │
  │ Function URL   │ ✗ MISS   │ no URL config — run 'setup url create'                   │
  │ CloudFront     │ ✓ OK     │ E1234567890ABC — Deployed                                │
  │ DNS            │ ⚠ DRIFT  │ wildcard points at d987.cloudfront.net (stale)           │
  └────────────────┴──────────┴──────────────────────────────────────────────────────────┘

  Overall: DRIFT (3 issues across 3 areas)

  Suggested actions:
    sg vault-publish setup iam update    # apply policy from Waker__Policy__Template
    sg vault-publish setup url create    # missing
    sg vault-publish setup dns update    # re-point wildcard to current CF distribution
```

## Machine output

```
$ sg vault-publish setup check --json
{
  "target_region": "eu-west-2",
  "target_account": "745506449035",
  "zone": "aws.sg-labs.app",
  "overall_state": "drift",
  "elapsed_ms": 2347,
  "acm": { ... },
  "iam": { "state": "drift", "missing_stmts": [ ... ], ... },
  ...
  "issues_total": 3,
  "actions_needed": [
    {"area": "iam",  "verb": "update", "reason": "missing ssm:GetParameter"},
    {"area": "url",  "verb": "create", "reason": "no URL config"},
    {"area": "dns",  "verb": "update", "reason": "wildcard points at stale CF domain"}
  ]
}
```

Same schema (`.json()` on the Type_Safe report). Suitable for CI
gates and monitoring tools.

## Where the magic happens

Each `Setup__*` class implements `check` as a pure read against AWS,
returning its own typed report. There is no shared "check engine" —
each area knows what its own checks look like.

`Setup__Service.check_all()` runs the area checks **in parallel**
where possible (e.g. ACM, IAM, Lambda can all be checked concurrently
since they're independent reads). CF check depends on knowing the
Function URL (to compare origin), so it runs after the URL check.

Total wall-clock for a full check on a real account: < 3 seconds.

## Per-area check

Each area also has its own `check` verb for targeted inspection:

```
sg vault-publish setup lambda check
sg vault-publish setup iam check --diff      # show inline policy diff vs template
sg vault-publish setup cf check
```

Same underlying method (`Setup__Lambda().check()`), same schema
(`Schema__Setup__Lambda__Report`), CLI just renders one area instead
of all.

## What check does NOT do

- **Doesn't run runtime probes.** No HTTP to the waker URL, no
  end-to-end "does cold start work" test. That's a separate verb
  (`sg vault-publish smoke-test`).
- **Doesn't check per-slug state.** Slug-specific health is
  `sg vault-publish status <slug>`.
- **Doesn't fix anything.** Read-only. Even when drift is obvious,
  `check` only reports it.
- **Doesn't depend on the CF distribution being deployed.** CF takes
  5–15 minutes to deploy. `check` reports `Status: InProgress` as a
  normal state, not an error.

## CI usage

```
# In .github/workflows/ci-setup-check.yml
- name: Verify setup
  run: |
    sg vault-publish setup check --json > setup.json
    jq -e '.overall_state == "ok"' setup.json
```

Fails the build if any area drifts. Catches "someone edited the
console" before it surfaces as a production incident.
