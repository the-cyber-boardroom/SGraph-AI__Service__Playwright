---
title: "04 — Phased implementation"
file: 04__phased-implementation.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
---

# 04 — Phased implementation

Aligned with the v2 brief's phase labels (P0 → P3) and the roadmap convention at `library/roadmap/phases/v0.1.9__phase-overview.md` (status icons: ✅ done, 🟡 in-flight, ❌ blocked, ⚠ at-risk). Every phase below starts ❌ (not started).

Each phase entry covers: **scope** (files touched / created), **tests added**, **success criteria**, **risks**, **dependencies**.

---

## Phase 0 — Validate the warm path today (NO CODE)

**Status:** ❌ not started. **Owner:** human operator (smoke test). **Size:** ~30 min.

**Scope:**

```
sg vault-app create --with-aws-dns hello-world \
                    --tls-mode letsencrypt-hostname \
                    --tls-hostname hello-world.sg-compute.sgraph.ai
# wait 3-5 minutes for cert-init + LE issuance
open https://hello-world.sg-compute.sgraph.ai/
```

**Tests added:** none — this is a one-shot manual validation.

**Success criteria:** browser-trusted cert, vault content visible, no warnings.

**Domain-strategy addendum** (per `07__domain-strategy.md §6`): also confirm the `sg-labs.app` hosted zone is resolvable from the operator's account (`aws route53 list-hosted-zones | grep sg-labs.app`) and that `SG_AWS__DNS__DEFAULT_ZONE=sg-labs.app sg aws dns zones default-zone` returns the right zone. Optional in P0 but cheap to do alongside the warm-path smoke test.

**Risks:** if this fails, every subsequent phase blocks until the substrate is fixed. Phase 0 must precede phase 1a.

**Dependencies:** none.

**Reality-doc update:** none yet (no code changed).

---

## Phase 1a — `sg vault-app stop` / `start` (SMALL)

**Status:** ❌ not started. **Owner:** Dev. **Size:** ~1 day.

**Scope (files touched/created):**

| Path | Action | What |
|------|--------|------|
| `sg_compute_specs/vault_app/service/Vault_App__Service.py` | EXTEND | + `stop_stack`, `start_stack`, `delete_per_slug_a_record`, `tls_hostname_from_tags` (helper) |
| `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Stop__Request.py` | NEW | One class per file |
| `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Stop__Response.py` | NEW | |
| `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Start__Request.py` | NEW | |
| `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Start__Response.py` | NEW | |
| `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` | EXTEND | + `stop` and `start` Typer commands |
| `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py` | EXTEND | When `max_hours > 0`, emit IMDSv2-derived `aws ec2 stop-instances` in the systemd timer (replacing `/sbin/shutdown -h now`) |
| `sg_compute_specs/vault_app/service/Vault_App__AWS__Client.py` | EXTEND | `launch.run_instance(..., shutdown_behavior='stop')` propagated |
| `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py` | EXTEND | + IAM inline policy statement granting `ec2:StopInstances` on `arn:aws:ec2:*:*:instance/*` with `aws:ResourceTag/StackType=vault-app` condition |
| `sg_compute_specs/vault_app/primitives/Safe_Str__EC2__Instance_Id.py` | NEW (if not present) | Used in the new schemas |
| `sg_compute_specs/vault_app/primitives/Safe_Int__Duration_Ms.py` | NEW (if not present) | Same |

**Tests added (under `sg_compute_specs/vault_app/tests/`):**

- `test_Vault_App__Service__stop_start.py` — happy paths + "instance not found" / "already running" / "DNS update failed but EC2 stopped" branches, using extended `Vault_App__AWS__Client__In_Memory`.
- `test_Vault_App__User_Data__Builder.py` — assert the rendered systemd-timer command equals the IMDSv2-stop snippet when `max_hours > 0`.
- `test_Cli__Vault_App.py` — extend to cover the two new commands (golden-file snapshot).

**Success criteria:**

```bash
sg vault-app create --with-aws-dns hello-world ...
# wait for healthy
sg vault-app stop hello-world         # → state=stopped; per-slug A record deleted
sg vault-app start hello-world         # → state=running; auto-DNS re-runs with new IP
open https://hello-world.sg-compute.sgraph.ai/   # works again after ≤60s DNS catch-up
```

**Risks:**

- The `aws ec2 stop-instances` IAM permission must NOT be `*` resource; it must be tag-conditioned to prevent a compromised instance from stopping unrelated stacks. The brief gets this right; Dev must implement the condition exactly.
- The boot script may need an `if docker compose ps -q | grep -q .` guard for `start` (containers already exist on restart). Confirm during integration test.
- `InstanceInitiatedShutdownBehavior='stop'` is a launch-template field — the brief assumes it's wired through `Vault_App__AWS__Client.launch.run_instance`; Dev must verify (`Vault_App__AWS__Client.py` not read in this plan).

**Domain-strategy addendum** (per `07__domain-strategy.md §3.5 / §6`):

- **GATING — Q13 audit.** Dev must first verify that `Vault_App__Service.delete_stack` (`sg_compute_specs/vault_app/service/Vault_App__Service.py:528`) already deletes the per-slug A record. If it does NOT, that's a substrate bad-failure (CLAUDE.md rule #27); fix it as the first commit of P1a so `stop_stack`'s DNS-delete can mirror the reference path.
- **Parametrise stop/start tests over zone-name** — run both `sg-compute.sgraph.ai` (default) and `sg-labs.app` (env-overridden via `SG_AWS__DNS__DEFAULT_ZONE`). Same code path; just ensures the override works.

**Dependencies:** Phase 0 passes.

**Reality-doc update:** add `vault-app stop / start` to `team/roles/librarian/reality/v0.1.31/01__playwright-service.md` (or the migrated `playwright-service/index.md`) under EXISTS.

---

## Phase 1b — Scaffold `sg_compute_specs/vault_publish/` (MEDIUM)

**Status:** ❌ not started. **Owner:** Dev. **Size:** ~2 days.

**Scope (all NEW under `sg_compute_specs/vault_publish/` unless noted):**

```
sg_compute_specs/vault_publish/
├── __init__.py                                     # empty per rule #22
├── manifest.py                                     # Enum stability + capabilities (see 03 §A.3)
├── version                                         # 'v0.1.0'
├── cli/
│   ├── __init__.py                                 # empty
│   └── Cli__Vault_Publish.py
├── service/
│   ├── __init__.py
│   ├── Vault_Publish__Service.py                   # register/unpublish/status/list (NOT bootstrap yet — phase 2d)
│   ├── Slug__Validator.py
│   ├── Slug__Registry.py
│   ├── Slug__Routing__Lookup.py
│   └── reserved/
│       ├── __init__.py
│       └── Reserved__Slugs.py
├── schemas/
│   ├── __init__.py
│   ├── Safe_Str__Slug.py
│   ├── Safe_Str__Vault__Key.py
│   ├── Enum__Slug__Error_Code.py
│   ├── Enum__Sg_Labs__Namespace.py                # vp, lab, ... (see 07__domain-strategy.md §1.5)
│   ├── Enum__Vault_Publish__State.py
│   ├── Schema__Vault_Publish__Entry.py
│   ├── Schema__Vault_Publish__Register__Request.py
│   ├── Schema__Vault_Publish__Register__Response.py
│   ├── Schema__Vault_Publish__Unpublish__Response.py
│   ├── Schema__Vault_Publish__Status__Response.py
│   ├── Schema__Vault_Publish__List__Response.py
│   ├── List__Slug.py
│   └── List__Schema__Vault_Publish__Entry.py
└── tests/
    ├── __init__.py
    ├── test_Safe_Str__Slug.py
    ├── test_Slug__Validator.py
    ├── test_Slug__Registry.py
    ├── test_Vault_Publish__Service.py
    └── test_Cli__Vault_Publish.py
```

Also EDIT:

- `sg_compute/cli/Cli__SG.py` — mount `vault-publish` + `vp` alias (mirroring lines 97-99 for vault-app).

**Tests added:**

| File | What it asserts |
|------|-----------------|
| `test_Safe_Str__Slug.py` | Charset, max-length, leading-/trailing-hyphen, double-hyphen reject |
| `test_Slug__Validator.py` | Reserved list + profanity returns the correct `Enum__Slug__Error_Code` |
| `test_Slug__Registry.py` | put/get/delete/list against `Parameter__In_Memory` (new fixture — see `05__test-strategy.md`) |
| `test_Vault_Publish__Service.py` | register → registry has entry + vault-app `create_stack` was called; unpublish reverse; status reads both registry + vault-app + DNS; list redacts vault keys |
| `test_Cli__Vault_Publish.py` | Golden-file snapshots of CLI output for each verb |

**Success criteria:**

```bash
sg vp register sara-cv --vault-key <k>
# → vault-app create_stack called with --with-aws-dns; SSM params written
sg vp list                                          # → ['sara-cv']
sg vp status sara-cv                                # → running, fqdn, vault_url
sg vault-app stop sara-cv                           # → from phase 1a; cold requests fail until phase 2d
sg vault-app start sara-cv
sg vp unpublish sara-cv                             # → vault-app deleted, registry entry gone, DNS clean
```

**Bootstrap stub:** `sg vp bootstrap` exists in CLI but prints `"PROPOSED — does not exist yet. Land in phase 2d."` and exits non-zero.

**Risks:**

- Slug primitive files: cherry-pick vs re-author (see `06__open-questions.md` Q2). Re-author is safer if the source branch has drifted from current Type_Safe versions; cherry-pick is faster.
- The brief's `Slug__Registry` uses SSM Parameter Store with one parameter per field. SSM has per-account limits (10K parameters in standard tier, 100K in advanced). For phase 1b this is fine; flag for the Librarian to track if the slug count goes >1000.

**Domain-strategy addendum** (per `07__domain-strategy.md §1 / §5 / §6`):

- **FQDN scheme is `<slug>.<namespace>.sg-labs.app`** (two-level under a namespace label). `Vault_Publish__Service.register` computes `f'{slug}.{namespace.value}.{zone_apex}'`.
- `Schema__Vault_Publish__Register__Request` gains a `namespace : Enum__Sg_Labs__Namespace = Enum__Sg_Labs__Namespace.VP` field — default `vp`, future lab spec can override.
- `Reserved__Slugs` seeded with namespace strings (`vp`, `lab`) **and** a generous shadow list pending Q15 decision (`www`, `api`, `admin`, `status`, `mail`, `cdn`, `auth`).
- **No new boto3 surface.** All Route 53 work composes existing `Route53__AWS__Client` methods (`upsert_record`, `delete_record`, `upsert_a_alias_record`, `find_hosted_zone_by_name`).

**Dependencies:** Phase 1a complete (the orchestrator delegates to `vault_app.stop_stack` / `start_stack` for the operator's manual cold-restart).

**Reality-doc update:** create `team/roles/librarian/reality/v0.1.31/sg-compute/vault_publish/index.md` (or migrate to the domain-tree style at `team/roles/librarian/reality/sg-compute/vault-publish/`). Mark "Phase 1b — scaffold + operator surface" under EXISTS; cold path still PROPOSED.

---

## Phase 2a — `sg aws cf` primitive (LARGE)

**Status:** ❌ not started. **Owner:** Dev. **Size:** ~3 days. **Largest single phase.**

**Scope:** ~30 NEW files under `sgraph_ai_service_playwright__cli/aws/cf/` (see `02__reuse-map.md §3` for the full list). Plus:

- `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` — EXTEND to mount `cf`.

**Tests added (~6 files under `tests/unit/sgraph_ai_service_playwright__cli/aws/cf/`):**

- `service/test_CloudFront__AWS__Client.py` — using `CloudFront__AWS__Client__In_Memory` (NEW): create / list / get / disable / delete + the disable-before-delete gate.
- `service/test_CloudFront__Distribution__Builder.py` — pure unit, no AWS dep.
- `service/test_CloudFront__Origin__Failover__Builder.py` — same.
- `cli/test_Cli__Cf.py` — golden-file CLI tests.
- `schemas/test_Schema__CF__*` (consolidated).

**Success criteria:** brief [`03 §4.6`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md) test list passes:

```bash
sg aws cf distributions list
sg aws cf distribution create --aliases '*.sg-compute.sgraph.ai' \
    --origin-fn-url https://xxx.lambda-url.eu-west-2.on.aws/ \
    --cert-arn arn:aws:acm:us-east-1:....
sg aws cf distribution disable <id>
sg aws cf distribution delete <id>
```

**Risks:**

- `osbot_aws.Cloud_Front` may grow distribution-management upstream while this is in flight — the module header must explicitly say "EXCEPTION — remove once osbot-aws covers create/update/delete/disable" so the migration is signposted.
- CloudFront distribution create + Deployed is ~15 min wall-clock. Integration tests gate behind `SG_AWS__CF__ALLOW_MUTATIONS=1` AND a `SG_AWS__CF__INTEGRATION=1` flag.
- The brief proposes pagination on `list_distributions` — verify upstream behaviour (the existing `Cloud_Front.distributions()` has a `# todo` for pagination per brief [`02 §7.5`](file:///tmp/vault-publish-brief/02__what-exists-today.md)). Dev must add it.

**Dependencies:** none — can run in parallel with 1a / 1b.

**Reality-doc update:** add `aws/cf/` to `team/roles/librarian/reality/v0.1.31/01__playwright-service.md` (or the migrated domain index).

---

## Phase 2b — `sg aws lambda` primitive (SMALL-MEDIUM)

**Status:** ❌ not started. **Owner:** Dev. **Size:** ~1.5 days.

**Scope:** ~21 NEW files under `sgraph_ai_service_playwright__cli/aws/lambda_/` (see `02__reuse-map.md §4`). Plus:

- `aws/cli/Cli__Aws.py` — EXTEND to mount `lambda`.

**Tests added:** ~5 files. Pattern matches phase 2a but smaller because most of the heavy lifting is in `osbot_aws.Deploy_Lambda` upstream.

**Success criteria:** brief [`05`](file:///tmp/vault-publish-brief/05__implementation-phases.md) phase-2b acceptance test:

```bash
sg aws lambda deployment deploy echo-lambda --code-path /tmp/echo-lambda --handler handler:handler
sg aws lambda url create echo-lambda --auth-type NONE
sg aws lambda url show echo-lambda
curl https://xxx.lambda-url.eu-west-2.on.aws/                  # → 'hello'
sg aws lambda deployment delete echo-lambda
```

**Risks:**

- `Deploy_Lambda.set_container_image` vs `add_folder` — two different deploy modes. The Waker in phase 2c uses `add_folder` + `add_osbot_aws` + `add_osbot_utils`; verify both modes are supported by `Lambda__Deployer`.
- Lambda Function URL auth modes: `AWS_IAM` and `NONE` are an enum — use `Enum__Lambda__Url__Auth_Type` (one file per enum, no Literals).

**Dependencies:** none — can run in parallel with 1a / 1b / 2a.

---

## Phase 2c — The Waker Lambda handler (MEDIUM)

**Status:** ❌ not started. **Owner:** Dev. **Size:** ~2 days.

**Scope:** all NEW under `sg_compute_specs/vault_publish/waker/`:

```
waker/
├── __init__.py
├── lambda_entry.py                    # entry — fires up Fast_API__Waker on import (see 03 §A.10)
├── Fast_API__Waker.py                 # pure class, no side effects (matches lambda_handler.py convention)
├── Waker__Handler.py                  # the state machine
├── Endpoint__Resolver.py              # abstract
├── Endpoint__Resolver__EC2.py         # phase 2c — uses osbot_aws.aws.ec2.EC2_Instance
├── Endpoint__Proxy.py                 # urllib3 reverse-proxy
├── Warming__Page.py                   # HTML generator
├── Slug__From_Host.py                 # composes Route53__Zone__Resolver
└── schemas/
    ├── __init__.py
    ├── Enum__Instance__State.py
    ├── Schema__Endpoint__Resolution.py     # (per delta A.8 — no tuples)
    ├── Schema__Subdomain__Parts.py         # (per 07__domain-strategy.md §1.4 / §5 — slug + namespace + apex; returned by Slug__From_Host instead of a tuple)
    └── Schema__Waker__Request_Context.py
```

Tests under `sg_compute_specs/vault_publish/tests/waker/`:

- `test_Slug__From_Host.py` — pure parse tests.
- `test_Endpoint__Resolver__EC2.py` — in-memory `EC2_Instance` subclass.
- `test_Endpoint__Proxy.py` — tiny inline aiohttp test server.
- `test_Warming__Page.py` — assert no-cache headers + auto-refresh meta.
- `test_Waker__Handler.py` — every state path (STOPPED, PENDING, RUNNING-but-not-healthy, RUNNING-and-healthy, unknown-slug, malformed-host).

**Success criteria:**

```bash
# local — no AWS
python -m sg_compute_specs.vault_publish.waker.lambda_entry --port 8090
curl -H 'Host: sara-cv.sg-compute.sgraph.ai' http://localhost:8090/
# → warming HTML (with the in-memory entry in 'stopped' state)
```

**Risks:**

- Lambda Web Adapter cold start with osbot-aws + osbot-utils + urllib3: the brief targets <200 ms; measure during phase 2d acceptance. (The lab brief's E30 would help if it has shipped.)
- BUFFERED invoke-mode caps response at 6 MB. The Waker should ideally check the response size and return a 502 with a clear message if exceeded, rather than failing opaquely. Phase 2c-followup if needed.

**Dependencies:** phase 2b (the Waker is deployed via `Lambda__Deployer` at bootstrap time, but the handler can be written + tested locally before that lands; integration deployment is gated on 2b).

---

## Phase 2d — `sg vault-publish bootstrap` (SMALL)

**Status:** ❌ not started. **Owner:** Dev. **Size:** ~1.5 days.

**Scope:**

- `sg_compute_specs/vault_publish/service/Vault_Publish__Service.py` — EXTEND with `bootstrap()` method per brief [`04 §6`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md).
- `sg_compute_specs/vault_publish/schemas/Schema__Vault_Publish__Bootstrap__Request.py` — NEW. Includes required `namespace : Enum__Sg_Labs__Namespace` field — bootstrap is per-namespace (see `07__domain-strategy.md §2.2 / §6`).
- `sg_compute_specs/vault_publish/schemas/Schema__Vault_Publish__Bootstrap__Response.py` — NEW.
- `sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py` — EXTEND (`bootstrap`, `waker info / logs / invoke` sub-verbs).

Tests:

- `test_Vault_Publish__Service__bootstrap.py` — bootstrap end-to-end with in-memory CF + Lambda + ACM clients.
- `test_Cli__Vault_Publish__bootstrap.py` — golden-file.

**Success criteria — the headline end-to-end on AWS (gated):**

```bash
sg vp bootstrap --zone sg-compute.sgraph.ai --cert-arn arn:aws:acm:us-east-1:...
# → CF distribution Deployed, wildcard ALIAS in Route 53, Waker Lambda deployed
sg vp register hello-world --vault-key <k>
sg vault-app stop hello-world
open https://hello-world.sg-compute.sgraph.ai/                  # → warming page
# (browser auto-refreshes; ~60-90s later)                       # → vault UI
open https://hello-world.sg-compute.sgraph.ai/                  # → direct hit on EC2; tail `sg vp waker logs` confirms no Lambda invocation
sg vp unpublish hello-world
```

**Risks:**

- The bootstrap is idempotent on paper. In practice, "create CF distribution if absent" needs to look up by `Comment` field or by stored ID; the latter requires `~/.sg/vault-publish-bootstrap.json` write (or SSM `/sg-compute/vault-publish/bootstrap/<namespace>/distribution-id` — note per-namespace prefix per `07__domain-strategy.md §4.3`). Use SSM — file-local config rots faster than tags.
- ACM cert lookup in `us-east-1` requires explicit region pinning; the existing `ACM__AWS__Client` defaults to the caller's region — verify it accepts a region override.
- **Cert provisioning is manual and per-namespace** (see `07__domain-strategy.md §2.2`). The operator must have issued `*.vp.sg-labs.app` in `us-east-1` before running `sg vp bootstrap --namespace vp`. Document the prerequisite at the top of the bootstrap CLI help string.

**Dependencies:** phases 1b, 2a, 2b, 2c all complete.

**Reality-doc update:** mark the full vault-publish cold path EXISTS in the domain index. Move the "PROPOSED — cold path" line into the EXISTS section.

---

## Phase 3 — Fargate / ECS target (OUT OF PLAN SCOPE)

Listed for completeness — the brief defers this to a separate brief. The plan deliberately does NOT cover it. Architect to write a follow-up brief when phase 2d is green.

---

## Phase 4 — Private VPC (OUT OF PLAN SCOPE)

Same — separate brief, deliberately deferred.

---

## Cross-phase dependencies

```
P0 ──► P1a ──► P1b ──┐
                     │
                     ├──► P2d ──► DONE
                     │
P2a ─────────────────┤
P2b ─────────────────┤
P2c ─────────────────┘
```

P2a / P2b / P2c can be picked up in parallel by additional Dev capacity (the lab brief notes the same observation about its own phasing).

**Critical path:** P0 → P1a → P1b → P2d (gated on P2a/P2b/P2c). The shortest serial path is P0 + P1a + P1b + P2a + P2b + P2c + P2d ≈ 12 working days for a single Dev.

---

## Cancel points

| Stop after | Value delivered |
|------------|-----------------|
| P0 | Empirical confirmation today's substrate handles the warm path |
| P1a | Cost story: stop/start lets operators idle stacks without losing state |
| P1b | Registry-backed operator workflow; manual cold-restart only |
| P2a / P2b / P2c (in any order) | Reusable platform primitives + locally-testable Waker |
| P2d | Full intended workflow live |

---

## Per-phase debrief

Per CLAUDE.md rule #26-28, **every slice gets a debrief** under `team/claude/debriefs/`, indexed in `team/claude/debriefs/index.md`. Each phase above is one slice. Architect prompts Dev to file the debrief at PR-close time and classifies failures as good (caught) or bad (silenced).
