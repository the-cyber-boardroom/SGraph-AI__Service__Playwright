---
title: "01 — Scope and architecture"
file: 01__scope-and-architecture.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 01 — Scope and architecture

The *what*. Five questions the harness exists to answer, four pillars the design rests on, and the module shape every sub-agent slots into.

---

## 1. The five questions (load-bearing claims in the v2 brief)

Every experiment in the catalogue maps back to one or more of these. (Source: `lab-brief/01 §1`.)

| # | Claim | What we don't actually know |
|---|-------|------------------------------|
| **Q1** | A more-specific Route 53 record beats the wildcard at every resolver | Every resolver? DoH gateways? Mobile carrier resolvers? How fast does the swap converge across the public-resolver set? |
| **Q2** | After `upsert_record`, INSYNC arrives in ~30–90 s | Distribution? p50? p99? Does it depend on zone size, change-batch backlog, time of day? |
| **Q3** | CloudFront falls through to the (single) origin on wildcard resolution | What does CF actually do when the origin times out, errors, throttles, returns 5xx? What's the retry behaviour? |
| **Q4** | The Waker Lambda serves a warming page in <200 ms cold-start | What is the *actual* distribution? With osbot-aws + osbot-utils added? Via Function URL? |
| **Q5** | Once the DNS swap happens, Lambda exits the data path within one TTL | Per resolver, or per client? How long does Chrome cache DNS? Firefox? Curl? Mobile Safari? |

---

## 2. Four pillars

| Pillar | What it says |
|--------|--------------|
| **Decomposition** | Break the v2 workflow into the smallest units that compose into a behavioural claim. ~22 components for 5 claims (see `lab-brief/02`). |
| **Safety** | No experiment may leak. Three independent cleanup mechanisms + TTL-stamped tags + session-level sweeper. Detailed in `02__common-foundation.md §4`. |
| **Visualisation** | Every experiment ships a Rich terminal table + an ASCII timeline (or histogram) + a JSON dump. The HTML viewer is optional. |
| **Reproducibility** | Same name pattern, same tags, same ledger format, same teardown order. Re-running gives comparable timings. Runs stored under `.sg-lab/runs/<utc-ts>__<exp-name>/` and diffable. |

---

## 3. Out of scope

To keep the harness focused:

- **No multi-region experiments.** Single region — `eu-west-2` for everything except ACM certs in `us-east-1`.
- **No multi-account experiments.** Single AWS account.
- **No IPv6.** Same logic applies; we measure v4 only.
- **No production traffic injection.** Real users never see lab resources.
- **No fault injection.** We measure steady state, not "what if Route 53 is degraded".
- **No load testing.** Single requests, repeated. Not concurrent thousands.
- **No long-running experiments.** Every experiment finishes within ~5 minutes worst case (a CF distribution create is the longest single step).
- **No CI gate.** Experiments run on-demand by a human operator under `SG_AWS__LAB__ALLOW_MUTATIONS=1`.

---

## 4. The cold-path request, decomposed

The full request lifecycle the v2 brief proposes, broken into 22 testable components. This is the menu the experiments draw from.

```
   user → https://<slug>.sg-compute.sgraph.ai/
        │
        ├─ D1   browser stub resolver decision
        ├─ D2   recursive resolver receives query
        ├─ D3   resolver walks delegation chain to R53 NS set
        └─ D4   one R53 NS answers — specific record beats wildcard (Q1)
                  │
                  │  wildcard → CF distribution
                  ▼
        ├─ C1   browser opens TLS to CF edge
        ├─ C2   CF terminates TLS using ACM wildcard cert
        ├─ C3   CF picks matching cache behaviour (CachingDisabled)
        └─ C4   CF forwards to origin = Lambda Function URL (Q3 behaviour)
                  │
                  ▼
        ├─ L1   CF opens TLS to Function URL
        ├─ L2   Function URL invokes Lambda (cold vs warm — Q4)
        └─ L3   Lambda runs FastAPI, parses Host, looks up registry,
                reaches EC2 / returns warming HTML
                  │
                  ▼   (warm path only)
        ├─ E1   Lambda opens TLS to EC2 public IP
        ├─ E2   vault-app's sg-send-vault answers
        └─ E3   Lambda streams response back upstream
                  │
                  ▼   (cold→warm flip)
        ├─ T1   Lambda upserts the specific A record
        └─ T2   resolvers re-query after wildcard TTL expires →
                see specific → direct path to EC2 (Q5)
```

Full table of 22 components with probe verb + measurement is in `lab-brief/02 §The component table`.

---

## 5. The four experiment categories

The 24 named experiments split cleanly into four categories — and that's how the Sonnet sub-agents are partitioned.

| Category | Experiment ID range | Sonnet agent | Notes |
|----------|--------------------|--------------|-------|
| **DNS** | E01-E14 | Agent A | Read-only (E01-E04) + mutating (E10-E14). Smallest dependency surface. |
| **CloudFront** | E20-E27 | Agent C | E20-E22 cheap read-only; E25-E26 Tier-2 (~25 min each); E27 owned by Agent D as the e2e composite. |
| **Lambda** | E30-E35 | Agent B | All Tier-1 mutations. Needs the in-tree lab Lambda functions and the Lambda primitive expansion. |
| **Transition** | E40-E42, plus E27 | Agent D | Composite — depends on A, B, C primitives. Lands last. |

A fifth optional agent (Agent E) ships the viewer + diff + HTML report.

---

## 6. Module shape

The whole harness lives under one folder, mirroring the `sg aws dns` shape:

```
sgraph_ai_service_playwright__cli/aws/lab/
├── __init__.py                       ← empty
├── cli/
│   └── Cli__Lab.py                   ← `sg aws lab …` Typer surface
├── service/
│   ├── Lab__Runner.py
│   ├── Lab__Ledger.py
│   ├── Lab__Sweeper.py
│   ├── Lab__Tagger.py
│   ├── Lab__Safety__Account_Guard.py
│   ├── Lab__Timing.py
│   ├── teardown/                     ← Lab__Teardown__{R53,CF,Lambda,ACM,EC2,SSM,IAM}.py
│   ├── experiments/
│   │   ├── Lab__Experiment.py        ← abstract base
│   │   ├── dns/                      ← Agent A
│   │   ├── cf/                       ← Agent C
│   │   ├── lambda_/                  ← Agent B
│   │   └── transition/               ← Agent D
│   ├── renderers/                    ← Agent E (table baseline lives in foundation)
│   ├── temp_clients/                 ← scheduled-for-deletion
│   └── lambdas/                      ← in-tree lab Lambdas (B's territory)
├── schemas/                          ← one Schema__Lab__* per file
├── enums/                            ← one Enum__Lab__* per file
├── primitives/                       ← Safe_Str__Lab__*, Safe_Int__*
└── collections/                      ← List__Schema__Lab__*
```

Full per-file breakdown is in `lab-brief/05 §1`. ~40 production files + ~30 test files, ~7800 total lines.

**Empty `__init__.py` everywhere.** Callers import the per-class fully-qualified path. No re-exports. (CLAUDE.md rule #22.)

---

## 7. CLI surface (target shape)

```
sg aws lab
├── list                              — every available experiment + tier + budget
├── show <experiment-id>              — metadata + last result snapshot
├── run <experiment-id> [opts...]     — run one experiment
│   --dry-run                         — print what would happen, no AWS calls
│   --json
│   --output-dir <path>               — override .sg-lab/runs/...
│   --tier-2-confirm                  — required for Tier-2
├── runs
│   list [--last N] [--experiment <id>]
│   show <run-id>
│   diff <run-id-A> <run-id-B>
├── sweep [--apply] [--older-than 1h] [--run-id <id>] [--mine] [--pending]
├── account
│   show                              — STS get-caller-identity + region
│   set-expected <account-id>
├── ledger
│   show <run-id>
│   replay <run-id>                   — re-run teardown for a past ledger (recovery)
└── serve [--port 8090]               — optional FastAPI viewer  (Agent E)
```

Mutation env var: `SG_AWS__LAB__ALLOW_MUTATIONS=1`.
Tier-2 also requires `--tier-2-confirm` (or an interactive `y/N`).

---

## 8. The two primitive expansions (Decisions #8 and #9)

The harness depends on capabilities `sg aws cf` and `sg aws lambda` don't have today. These are folded into this milestone — Agent C builds the CF additions while building the CF experiments; Agent B builds the Lambda additions while building the Lambda experiments.

### `sg aws cf` — additions (Agent C)

| New verb | Purpose | Used by |
|----------|---------|---------|
| `distribution update` | Edit cache behaviour, alias list, origin (without delete-recreate) | E25, E26, v2 brief phase 1 |
| `distribution invalidate` | Create + monitor a cache invalidation | E25 cleanup, v2 brief operationally |
| `distribution origin-group create` | Build CF origin-group (primary + secondary failover) | E26 `--case timeout`, v2 brief phase 2b |
| `distribution tags {list,set,remove}` | Tag management | Lab tagging convention; sweeper |
| `oac {create,list,delete}` | Origin Access Control objects (for future S3 origins) | v2 brief future hardening |

### `sg aws lambda` — additions (Agent B)

| New verb | Purpose | Used by |
|----------|---------|---------|
| `<name> deploy-from-image` | Deploy from an ECR container image instead of zip | v2 brief (waker as container) |
| `<name> alias {create,list,update,delete}` | Lambda alias management | E33, v2 brief versioning |
| `<name> permissions {add,list,remove}` | Resource-policy statement management (e.g. allow CF to invoke) | E25, E26 (CF→Lambda invoke perm) |
| `<name> concurrency {get,set,clear}` | Reserved-concurrency control | Lab safety guard (cap lab Lambdas to 2) |
| `<name> env {get,set,unset}` | Env-var management without full `--update-function-configuration` | Convenience verb, used everywhere |

The current `sg aws lambda` `<name> tags / versions / aliases` placeholders get filled in as part of this expansion.

---

## 9. What this brief is NOT

(Same list as `lab-brief/README §What this brief is NOT`, kept here for the Dev session.)

- **Not a replacement for unit tests.** Unit tests with in-memory clients run on every push; the harness runs against real AWS.
- **Not a CI gate.** Experiments run on demand, by a human operator.
- **Not a load test.** Single requests, repeated. Not stress-tests.
- **Not a substitute for the v2 brief landing.** This is a measurement scaffold; v2 is the system being measured.
- **Not a permanent fixture.** Once a behaviour is well-understood, its experiment can be retired (or kept as a weekly regression check).
