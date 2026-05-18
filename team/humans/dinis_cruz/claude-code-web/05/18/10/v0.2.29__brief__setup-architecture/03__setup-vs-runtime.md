---
title: "03 — Setup vs runtime"
file: 03__setup-vs-runtime.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 03 — Setup vs runtime

## The two operational modes

```
                        SETUP                                         RUNTIME
                        ─────                                         ───────

Frequency               Once per account / region                    Many times per day
Cost of change          Slow (CF takes 5–15 min to deploy)           Fast (Route 53 in seconds)
Idempotency             Critical — re-runs must be safe              Per-slug uniqueness enforced
                                                                     by registry
Affected resources      ACM cert                                     Route 53 per-slug A record
                        CloudFront distribution                      SSM Parameter Store per-slug entry
                        Lambda function (code + config)              EC2 instance (start/stop)
                        Lambda Function URL
                        IAM execution role + policy
                        Route 53 wildcard ALIAS to CF
                        S3 bucket for layer storage (optional)

Operator verbs          setup check                                  register / unpublish
                        setup * create / update / delete             start / stop
                        bootstrap / teardown                         status / list

CLI surface             sg vault-publish setup ...                   sg vault-publish ...
                        sg vault-publish bootstrap                   sg vault-app ...
                        sg vault-publish teardown
```

## Why the split matters

### Different audiences

- **Setup** is operator/SRE work. Done once per environment, requires
  AWS console-level permissions (CF, ACM, IAM). The operator wants
  confidence that the environment is correctly provisioned.
- **Runtime** is application work. Done by anyone who can register a
  slug. The application wants speed and reliability, not the ability
  to mutate IAM.

Conflating them — as today's bootstrap does — means anyone who can
call `bootstrap` can also stomp on the CloudFront distribution. Bad.

### Different failure modes

- **Setup failures** are loud and obvious — `bootstrap` raises and
  nothing works. Recovery is "fix the script, re-run".
- **Runtime failures** are subtle — a slug stops working but the
  infrastructure is fine. Recovery is "look at the slug-specific
  state, not the global state".

The same `check` is the wrong shape for both. Setup's check returns
a summary of every resource. Runtime's check returns a per-slug
status.

### Different change rates

- ACM cert: created once, lasts a year, auto-renewed by ACM.
- CF distribution: created once, edited rarely (e.g. when origin URL
  changes after a Lambda re-deploy that recreates the URL).
- Lambda code: edited per release.
- IAM policy: edited when we add permissions (we just added
  `ssm:GetParameter` — that's a setup change, not a runtime one).
- Route 53 wildcard: created once, never edited.
- Route 53 per-slug: created/deleted constantly as instances start/stop.
- SSM per-slug: created/deleted per `register/unpublish`.

The runtime resources already have proper CRUD via the existing
service (`Vault_Publish__Service.register` etc.). The setup resources
need the same treatment.

## What stays under `vault_publish/` vs `setup/`

```
sg_compute_specs/vault_publish/
├── cli/Cli__Vault_Publish.py            # runtime CLI (existing)
│   └── ...register / unpublish / status / list
├── schemas/                              # runtime + setup share these
├── service/                              # runtime services
│   ├── Slug__Registry.py                 # SSM CRUD
│   ├── Slug__Validator.py
│   └── Vault_Publish__Service.py         # register/unpublish/status/list
│                                         # bootstrap MOVES to setup/
├── waker/                                # Lambda code
└── setup/                                # NEW: per-area setup
    ├── cli/
    │   └── Cli__Setup.py                 # sg vault-publish setup ...
    ├── service/
    │   ├── Setup__Service.py             # orchestrator
    │   ├── Setup__ACM.py                 # acm check / update
    │   ├── Setup__CloudFront.py          # cf check / create / update / delete
    │   ├── Setup__Lambda.py              # lambda check / deploy / delete
    │   ├── Setup__Function_URL.py        # url ensure / delete
    │   ├── Setup__IAM.py                 # role + policy check / update
    │   └── Setup__S3.py                  # layer bucket — phase B only
    └── schemas/
        ├── Schema__Setup__Report.py      # check returns this
        ├── Schema__Setup__Area__Report.py
        └── Enum__Setup__State.py         # OK / MISSING / DRIFT / ERROR
```

The existing `Vault_Publish__Service.bootstrap()` becomes
`Setup__Service.converge()` and delegates to each `Setup__*` class.

## What this brief deliberately defers

- **Multi-region / multi-account.** Setup is per (account, region).
  We do not address how to provision the same setup in three regions.
  That's a follow-up.
- **Atomic teardown.** `teardown` runs deletes in order with best
  effort. We do not implement transactional rollback.
- **CI integration.** `sg vault-publish setup check` should run as a
  smoke test in CI, but that's a separate piece of work.
- **The runtime path.** `register / unpublish / status / list` are
  not touched. They continue to live in `service/` and continue to
  work the same way.
