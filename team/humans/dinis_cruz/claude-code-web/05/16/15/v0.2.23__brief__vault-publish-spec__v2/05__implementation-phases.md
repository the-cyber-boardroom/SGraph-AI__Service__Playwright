---
title: "05 — Implementation phases"
file: 05__implementation-phases.md
author: Claude (Architect)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 05 — Implementation phases

How to land this. Each phase is independently shippable, independently testable, and unlocks something visible.

Estimates are "small / medium / large" relative to a focused Dev session. Slices roughly map to one PR each.

---

## Phase 0 — Validate the warm path (zero code)

**Goal:** prove the end-state warm path works today with existing code. No commits.

**Acceptance:**
```
sg vault-app create --with-aws-dns hello-world --tls-mode letsencrypt-hostname \
                    --tls-hostname hello-world.sg-compute.sgraph.ai

# wait ~3-5 minutes for cert-init's DNS-wait + LE issuance
open https://hello-world.sg-compute.sgraph.ai/
# → vault UI loads, browser-trusted cert, no warnings
```

**Why first:** it validates every assumption the brief makes about the substrate (vault-app image, auto-DNS, letsencrypt-hostname mode, the routing path) without any new code. If this doesn't work, the whole plan needs revisiting before phase 1.

**Owner:** human operator (one-shot manual test).

---

## Phase 1a — `sg vault-app stop` / `start` (SMALL)

**Goal:** add stop/start verbs to the existing vault-app spec; auto-DNS re-runs on `start`.

**Scope** (all in `sg_compute_specs/vault_app/`):
- `Vault_App__Service.stop_stack` + `start_stack` methods (see [`03 §3.2`](03__sg-compute-additions.md#32-service-methods))
- Schemas: `Schema__Vault_App__Stop__Response`, `Schema__Vault_App__Start__Response`
- CLI: `sg vault-app stop <name>` + `sg vault-app start <name>` in `cli/Cli__Vault_App.py`
- Modify `Vault_App__AWS__Client.launch.run_instance(...)` to pass `InstanceInitiatedShutdownBehavior='stop'` so the in-instance idle hook stops rather than terminates
- Modify `Vault_App__User_Data__Builder.render(...)` — when `max_hours > 0`, the systemd timer calls `aws ec2 stop-instances --instance-ids $(curl ...IMDSv2...)` instead of `/sbin/shutdown -h now`
- Add `ec2:StopInstances` (with `aws:ResourceTag/StackType=vault-app` condition) to the `playwright-ec2` IAM profile

**Tests:** in-memory `Vault_App__AWS__Client` extended with stop/start state transitions; tests cover both happy paths + the "instance not found" / "already running" / "DNS update failed but EC2 started OK" branches.

**Acceptance:**
```
sg vault-app create --with-aws-dns hello-world ...
# wait for healthy
sg vault-app stop hello-world
# → instance state = stopped; A record deleted
sg vault-app start hello-world
# → instance state = running; new public IP in A record
open https://hello-world.sg-compute.sgraph.ai/   # works again after ~60s DNS catch-up
```

**Risk to watch:** does the vault-app boot script handle "containers already exist"? If `docker compose up -d` is idempotent (it is), no change needed. If the user-data script unconditionally pulls + runs, we need to guard with `if docker compose ps -q | grep -q .`.

**Owner:** Dev. Size: ~1 day.

---

## Phase 1b — Scaffold `sg_compute_specs/vault_publish/` (MEDIUM)

**Goal:** the spec is on the catalogue and the operator surface works, using only existing primitives (no CloudFront / Lambda yet — cold requests fail until phase 2).

**Scope** (all in `sg_compute_specs/vault_publish/`):

- Manifest + folder skeleton (per [`04 §1`](04__vault-publish-spec.md#1-folder-layout))
- **Port** from top-level `vault_publish/`:
  - `Safe_Str__Slug` + `Slug__Validator` + `Reserved__Slugs` + `Enum__Slug__Error_Code` + their tests
- **New**:
  - `Slug__Registry` (SSM Parameter Store; uses `osbot_aws.Parameter`)
  - `Vault_Publish__Service.register / unpublish / status / list` (orchestrator)
  - `Schema__Vault_Publish__Entry` + the request/response schemas
  - `Cli__Vault_Publish` + mount under `sg vault-publish` / `sg vp` in `sg_compute/cli/Cli__SG.py`
  - Tests: in-memory `Parameter` subclass, in-memory `Vault_App__Service` for the orchestrator tests

**At end of phase 1b:**
- `sg vault-publish register sara-cv --vault-key <k>` → calls `sg vault-app create --with-aws-dns sara-cv --seed-vault-keys <k> ...` + writes registry
- `sg vault-publish list` / `status` / `unpublish` all work
- Operator can manually `sg vault-app stop` an idle slug; cold requests will fail (no CF / Lambda yet) — known limitation, documented in `sg vp status` output

**Decommission:** the top-level `vault_publish/` package + tests are deleted in this phase. The CLI mount in `sg_compute/cli/Cli__SG.py` switches to the new spec.

**Acceptance:**
```
sg vp bootstrap                                  # no-op stub in phase 1b (returns "not yet wired")
sg vp register sara-cv --vault-key <k>
sg vp list                                       # → ['sara-cv']
sg vp status sara-cv                             # → running, fqdn, vault_url
sg vault-app stop sara-cv                        # → stopped; cold requests will fail
sg vault-app start sara-cv
sg vp unpublish sara-cv
```

**Owner:** Dev. Size: ~2 days.

---

## Phase 2a — `sg aws cf` primitive (LARGE)

**Goal:** complete the CloudFront primitive (the biggest single piece of net-new code in the brief).

**Scope** (all in `sgraph_ai_service_playwright__cli/aws/cf/`): per [`03 §4`](03__sg-compute-additions.md#4-sg-aws-cf--cloudfront-primitive).

- `CloudFront__AWS__Client` (sole boto3 boundary; ~250 lines; module header notes the osbot-aws gap)
- `CloudFront__Distribution__Builder` (pure config-builder)
- `CloudFront__Origin__Failover__Builder` (origin-group config)
- `Cli__Cf` with sub-typers (`distributions`, `distribution`, `origins`, `invalidations`) — ~500 lines
- Schemas / enums / primitives / collections (per [`03 §§4.3–4.5`](03__sg-compute-additions.md#43-schemas))
- `SG_AWS__CF__ALLOW_MUTATIONS=1` gate on mutations
- In-memory test client; ~6 test files

**Acceptance:**
```
sg aws cf distributions list                                        # → table of all distributions
sg aws cf distribution create --aliases '*.sg-compute.sgraph.ai' \
    --origin-fn-url https://xxx.lambda-url.eu-west-2.on.aws/ \
    --cert-arn arn:aws:acm:us-east-1:....
sg aws cf distribution show <id>
sg aws cf distribution disable <id>
sg aws cf distribution delete <id>
```

**Owner:** Dev. Size: ~3 days. Largest single phase in the brief.

---

## Phase 2b — `sg aws lambda` primitive (SMALL-MEDIUM)

**Goal:** Typer wrapper over `osbot_aws.Deploy_Lambda`.

**Scope** (all in `sgraph_ai_service_playwright__cli/aws/lambda_/`): per [`03 §5`](03__sg-compute-additions.md#5-sg-aws-lambda-primitive).

- `Lambda__Deployer` (Type_Safe wrapper over `Deploy_Lambda`)
- `Lambda__AWS__Client` (thin convenience over `osbot_aws.aws.lambda_.Lambda`)
- `Lambda__Url__Manager`
- `Cli__Lambda` with sub-typers (`deployments`, `deployment`, `url`, `invoke`, `logs`)
- Schemas / enums / primitives
- `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` gate

**Acceptance:**
```
# Tiny smoke-test Lambda
mkdir -p /tmp/echo-lambda && cat > /tmp/echo-lambda/handler.py <<'EOF'
def handler(event, context):
    return {'statusCode': 200, 'body': 'hello'}
EOF
sg aws lambda deployment deploy echo-lambda --code-path /tmp/echo-lambda \
    --handler handler:handler
sg aws lambda url create echo-lambda --auth-type NONE
sg aws lambda url show echo-lambda                              # → https://xxx.lambda-url...
curl https://xxx.lambda-url.eu-west-2.on.aws/                  # → hello
sg aws lambda deployment delete echo-lambda
```

**Owner:** Dev. Size: ~1.5 days.

---

## Phase 2c — The Waker Lambda (MEDIUM)

**Goal:** write the handler that lives inside the Lambda deployed by phase 2b.

**Scope** (all in `sg_compute_specs/vault_publish/waker/`): per [`04 §5`](04__vault-publish-spec.md#5-the-waker-lambda-handler).

- `lambda_entry.py` (FastAPI + Lambda Web Adapter)
- `Waker__Handler` (the state machine — ~150 lines)
- `Endpoint__Resolver` (abstract) + `Endpoint__Resolver__EC2` (~50 lines)
- `Endpoint__Proxy` (urllib3 reverse-proxy — ~100 lines)
- `Warming__Page` (HTML generator — ~30 lines)
- `Slug__From_Host` (parses Host header → slug; reuses `Route53__Zone__Resolver` shape — ~30 lines)
- Tests: in-memory `EC2_Instance` and `Endpoint__Resolver`; full state-machine coverage

**Local testability:** the Lambda is just a FastAPI app. `python -m sg_compute_specs.vault_publish.waker.lambda_entry` runs it under uvicorn with `Endpoint__Resolver__EC2__In_Memory` injected — same pattern as the existing `vp-server` script. Tests cover every state without deploying to AWS.

**Acceptance:**
```
# Local
python -m sg_compute_specs.vault_publish.waker.lambda_entry --port 8090
# seed an in-memory entry, hit it
curl -H 'Host: sara-cv.sg-compute.sgraph.ai' http://localhost:8090/
# → warming HTML (stopped); start the in-memory EC2; → proxied content
```

**Owner:** Dev. Size: ~2 days.

---

## Phase 2d — `sg vault-publish bootstrap` (SMALL)

**Goal:** wire phase 2a + 2b + 2c together so the end-to-end cold path works.

**Scope** (in `sg_compute_specs/vault_publish/`):

- `Vault_Publish__Service.bootstrap()` (per [`04 §6`](04__vault-publish-spec.md#6-the-bootstrap-flow))
- `sg vp bootstrap` CLI verb
- `sg vp waker info / logs / invoke` sub-verbs

**Acceptance — the headline end-to-end test:**
```
sg vp bootstrap --zone sg-compute.sgraph.ai --cert-arn arn:aws:acm:us-east-1:...
# → CF distribution Deployed, wildcard ALIAS in Route 53, Waker Lambda deployed

sg vp register hello-world --vault-key <k>
sg vault-app stop hello-world                                          # idle the instance
open https://hello-world.sg-compute.sgraph.ai/                         # → warming page
# (browser auto-refreshes; ~60-90s later)
                                                                       # → vault UI
open https://hello-world.sg-compute.sgraph.ai/                         # second request: direct to EC2 (Lambda not invoked)

sg vp unpublish hello-world
sg vp bootstrap --delete                                                # phase-2d-followup: tear-down
```

At end of phase 2d the brief's headline workflow runs end-to-end on AWS.

**Owner:** Dev. Size: ~1.5 days (mostly bootstrap orchestration + integration test).

---

## Phase 3 — Fargate / ECS target (FUTURE)

**Goal:** swap-in target for `Endpoint__Resolver` — same Waker handler, different backend.

**Scope:**
- `Endpoint__Resolver__Fargate` using `osbot_aws.aws.ecs.ECS_Fargate_Task`
- Probably a parallel `sg_compute_specs/fargate_app/` spec for the substrate (the equivalent of `vault_app/` for tasks instead of EC2)
- Waker `Endpoint__Resolver` factory chooses EC2 vs Fargate based on the slug's registry entry (new field `compute_type`)

**Owner:** Architect + Dev. Size: separate brief.

---

## Phase 4 — Private VPC (FUTURE)

**Goal:** EC2 in private subnet; Lambda VPC-attached; no public IPs.

**Scope:**
- Lambda config: `vpc_config` (security group + subnets)
- Vault-app: launch into private subnet; `Endpoint__Resolver__EC2.resolve` returns the private IP
- DNS strategy: per-slug A record now holds the private IP; resolvable only via VPC-side resolver. Public DNS (the `*.sg-compute.sgraph.ai` wildcard) always goes through CF + Lambda. Warm path is harder; we may concede that phase 4 = "Lambda always in path, no DNS-swap" and accept the cost.
- New IAM scoping (VPC ENI permissions on the Lambda role)

**Owner:** Architect + Dev. Size: separate brief, deliberately deferred.

---

## Phase ordering rationale

```
0   (free)        Validate that today's pieces compose right
1a  (small)       Stop/start unlocks the cost story without any new primitives
1b  (medium)      The spec exists; operator surface works manually
2a  (large)       CloudFront primitive — gates everything below
2b  (small)       Lambda primitive — gates the Waker
2c  (medium)      Waker handler — runs locally before deploy
2d  (small)       Wire bootstrap → end-to-end cold path works
3   (future)      Fargate
4   (future)      Private VPC
```

**Critical paths:**

- 2a is the big rock. It can be picked up in parallel with 1a / 1b by a second Dev.
- 1a → 1b: required ordering. 1b uses `sg vault-app stop / start` from the orchestrator.
- 2a + 2b + 2c → 2d: any ordering inside the trio works; 2d needs all three.

**Cancel points** (where we can ship-and-stop if priorities change):

- After 1a: cost story done; manual operator workflow.
- After 1b: registry-backed operator workflow; manual cold-restart.
- After 2d: full intended workflow live.

---

## What does not get built (out of scope of every phase)

These are explicit and intentional:

- The v0.2.11 manifest interpreter / verifier / signing scheme — dead, deleted in phase 1b.
- The bespoke `Instance__Manager` / `Control_Plane__Client` from the v0.2.11 work — replaced by direct calls to `sg vault-app` and the existing host-control-plane.
- Elastic IPs — never needed.
- Per-slug ALB target groups — never needed in phases 1-2.
- A new container image — never. The `sg-send-vault` image already serves what we need.
- A bespoke "vault-publish manifest" schema — deleted with the v0.2.11 pack.
- The two SG/Send open questions (#3 fetch contract, #4 signing scheme) from the v0.2.11 pack — they disappear; the only remaining SG/Send dependency is `sgit clone <vault-key>` which already runs on the box at boot time.

---

## Definition of done — at the end of phase 2d

A reviewer (you) can run, on a clean AWS account with one bootstrap step:

```
sg vp bootstrap --zone sg-compute.sgraph.ai --cert-arn arn:aws:acm:us-east-1:...
sg vp register hello-world --vault-key <k>
```

…and then, **from any browser anywhere in the world**, `https://hello-world.sg-compute.sgraph.ai/` returns the vault UI. Idle the instance via `sg vault-app stop`, hit the URL again — get a warming page that auto-refreshes into the vault UI within ~60–90 s. The first warm-path request after that is a direct hit on the EC2 — confirmed by tailing `sg vp waker logs` and seeing no Lambda invocation.

That is the brief.
