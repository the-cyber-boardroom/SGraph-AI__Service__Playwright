---
title: "Architecture Brief — SG/API + Vault App on a Container-Image Lambda (vs ZIP)"
file: architecture__sg-api-vault__lambda-container-vs-zip.md
author: Architect (Claude)
date: 2026-06-13 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ dev (v0.2.x line; reality doc at v0.2.30 in-progress)
status: BRIEF — no code, no commits. For human (Dinis) decision before any Dev work.
role: Architect
scope: Decision support for deploying SG/API (Playwright FastAPI service) + Vault App capabilities to AWS Lambda using a container image instead of a zip package.
grounding: team/roles/librarian/reality/{index,vault,infra,sg-compute,playwright-service}/index.md
---

# Architecture Brief — SG/API + Vault App on a Container-Image Lambda (vs ZIP)

> **Reality-doc rule applied.** Every "exists today" claim below is cross-checked against the reality docs and the cited source files. Anything not confirmed is labelled **PROPOSED — does not exist yet.** The headline finding is that **no container-image Lambda path exists in this repo today** — neither for SG/API nor the Vault App — so the entire subject of this brief is greenfield. What *does* exist is reusable tooling (a zip-only Lambda deployer, an ECR image-mirror, a Fargate vault orchestrator) that a container-image Lambda build would lean on.

---

## 1. Current state (grounded)

### 1.1 SG/API (the Playwright FastAPI service) — how it deploys today

| Fact | Evidence |
|------|----------|
| The service is **one Docker image**, `diniscruz/sg-playwright`, pushed to **Docker Hub** (not ECR, not Lambda). | `sg_compute_specs/playwright/Dockerfile` header: "v0.2 — Docker Hub, no Lambda Web Adapter"; reality `playwright-service/index.md` line 8; `infra/index.md` line 14. |
| Base image: `mcr.microsoft.com/playwright/python:v1.58.0-noble` (Chromium + system deps pre-installed). | `Dockerfile:18`; `requirements.txt:5` pins `playwright==1.58.0` to match. |
| Container entrypoint is **plain uvicorn on :8000** — `CMD ["python3","-m","sg_compute_specs.playwright.core.fast_api.lambda_handler"]`. The module name is historical; it runs uvicorn, **not** a Lambda adapter. | `Dockerfile:70`; `sg_compute_specs/playwright/core/fast_api/lambda_handler.py:17-25`. |
| **The Lambda / ECR / S3-zip deploy path for SG/API was RETIRED in v0.2.11.** The Lambda Web Adapter was dropped post-v0.2.11. | `infra/index.md` line 33; `playwright-service/index.md` line 8; architect review `team/roles/architect/reviews/05/14/v0.2.6__playwright-deployment-simplification.md` (cited by the reality doc). |
| **Live deployment targets today:** laptop / CI / EC2 host-plane (via `sg-compute spec playwright create`) / Fargate (as a container in the vault stack). The public dev endpoint `https://dev.playwright.sgraph.ai/` is CloudFront in front of the Docker Hub image **running on EC2** — **the Lambda Function URL is gone.** | `playwright-service/index.md` lines 178, 182-192; `infra/index.md` lines 83-92. |
| The `lambda_handler.py` file is kept as a **parity stub only** ("kept for parity, not in the live deployment path"). | `playwright-service/index.md` lines 8, 134. |

**Reconciliation of the CLAUDE.md vs Dockerfile contradiction (the task flagged this).** CLAUDE.md still says "16 direct endpoints… Lambda Web Adapter — HTTP translation, not Mangum" and the stack table lists "AWS Lambda Web Adapter 1.0.0". **Those statements are stale.** The reality docs and the Dockerfile header are authoritative and agree: **the LWA path for SG/API was removed.** The service now ships as a Docker Hub OCI image with no LWA, no `lambda_entry.py`, no `/var/task`. So when this brief proposes putting SG/API back on Lambda, it is **re-introducing a retired capability in a new form (container image), not continuing an existing one.**

### 1.2 The *other* Lambdas in the repo — and how they actually deploy (ZIP + Mangum, NOT LWA)

There ARE live Lambdas in this repo, but none of them are SG/API and **none of them use LWA**:

| Lambda | Pattern | Evidence |
|--------|---------|----------|
| `sg-compute-vault-publish-waker` | **ZIP** code + Mangum handler + a **combined-dependency zip loaded from S3 at cold start** onto `sys.path`. | `sg_compute_specs/vault_publish/lambdas/waker/lambda_entry.py:19-41`; `waker__config.py` (deps = `osbot-fast-api-serverless` which pulls `fastapi+starlette+mangum` transitively). |
| `sg-compute-vault-publish-admin` | Same ZIP+Mangum+S3-deps shape; own IAM role + CloudFront distribution. | `vault_publish/lambdas/admin/lambda_entry.py`; reality `sg-compute/index.md` history (v0.1.16). |
| `sg_edge` Edge Waker | Same ZIP+Mangum+S3-deps shape via `Serverless__Fast_API`. | `sg_compute_specs/sg_edge/lambdas/edge_waker/lambda_entry.py`. |
| `sp-playwright-cli` Lambda | The **CLI** (not the browser service) on `public.ecr.aws/lambda/python:3.12` (**no Chromium**), 1024 MB / 120 s / Function URL AuthType=NONE. | `infra/index.md` lines 59-67; `cli/ec2.md`. |

**Takeaway:** the repo's *real, working* Lambda convention is **ZIP + Mangum + an S3 combined-deps loader** (the "osbot serverless shape"), driven by `Lambda__Deployer.deploy_from_folder(...)`. **LWA appears in CLAUDE.md and one parity stub but is not used by any live Lambda.** Whoever wrote the task prompt's premise ("Lambda Web Adapter requirement for FastAPI") should know the in-repo precedent went the *other* way (Mangum, zip, S3 deps) precisely because these Lambdas are small and have no Chromium.

### 1.3 The ZIP Lambda deploy tooling — what it can and cannot do

`sgraph_ai_service_playwright__cli/aws/lambda_/service/Lambda__Deployer.py`:

- `deploy_from_folder(req, ...)` zips a folder, optionally builds+uploads a **combined third-party dependency zip to S3** (`combined_dependencies=(base_name, packages)`), optionally uploads the code zip to an **IFD-versioned S3 key** (`{account}--osbot-lambdas--{region}` bucket), then `create_function` / `update_function_code` + `update_function_configuration`. Documented `boto3` exception in the header.
- Request schema `Schema__Lambda__Deploy__Request`: `name / folder_path / handler / role_arn / runtime / memory_size=256 / timeout=900 / description`. **Default timeout is the Lambda max, 900 s; default memory 256 MB.**
- Runtime enum `Enum__Lambda__Runtime`: `python3.11 / 3.12 / 3.13` only.
- CLI verb: `sg aws lambda <name> deploy --code-path … --handler … --role-arn … --runtime … --memory … --timeout …`, gated by `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` (`cli/verbs/verb_deploy.py`).

**Hard limit of this tooling, confirmed by reading the code:** it ONLY does `Code={'ZipFile': …}` or `Code={'S3Bucket',…'S3Key'}` (`Lambda__Deployer.py:111-114`). **There is no `PackageType='Image'` / `Code={'ImageUri': …}` branch anywhere — grep across `sgraph_ai_service_playwright__cli`, `sg_compute`, `sg_compute_specs` returns zero hits for container-image Lambda.** The runtime enum has no image option. **So the existing deployer cannot deploy a container-image Lambda. That branch must be built.**

### 1.4 Vault App — how it deploys today

The "Vault App" is a **4-container Docker stack**, of which `sg-send-vault` is the only externally-reachable surface and the only stateful one:

| Container | Image | Role | State |
|-----------|-------|------|-------|
| `sg-send-vault` | `diniscruz/sg-send-vault` | vault storage + UI; port 8080 (sole external port) | **`/data` volume** in compose; but on Fargate forced to `SEND__STORAGE_MODE=memory` |
| `host-plane` | `diniscruz/sg-host-control` | control-plane FastAPI (Docker socket) | — |
| `sg-playwright` | `diniscruz/sg-playwright` | browser automation (SG/API itself!) | — |
| `agent-mitmproxy` | ECR `agent_mitmproxy` | passive capture, internal only | — |

Evidence: `sg_compute_specs/vault_app/docker/compose/docker-compose.yml`.

**Production vault deployment is Fargate (VAF), added v0.2.33** (`sg-compute/index.md` lines 112-152; reality `vault/index.md`):

- CLI: `sg vault-app fargate setup …` (cluster-level: ECS cluster, task-def, ECR repo, IAM execution role, CloudWatch log group) + `… start/stop/restart/health/url/…` (per vault session). Mutation gate `SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1`.
- `Vault_App__Fargate__Starter.start()` is a 6-phase orchestrator: RESOLVE_CONFIG → RUN_TASK → WAIT_RUNNING → RESOLVE_ENI → DNS_UPSERT (Route53 A-record) → WAIT_HEALTH (`fargate/service/Vault_App__Fargate__Starter.py`). Task CPU/mem default `512`/`1024` (`Vault_App__Fargate__Spec.py`).
- `Vault_App__Fargate__Image__Mirror` mirrors a public image (e.g. `diniscruz/sg-send-vault:latest`) **into ECR** — pull, tag, push, with `--platform linux/amd64` pinning and idempotency. **This is the reusable image-into-ECR seam.** (`fargate/service/Vault_App__Fargate__Image__Mirror.py`.)
- **Vault keys / secrets are injected at task-run time as container env vars**, not from Secrets Manager: `Vault_App__Fargate__Spec.env_for_run(access_token, seed_vault_keys, …)` returns `SEND__ACCESS_TOKEN`, optional `SEND__SEED_VAULT_KEYS`, etc., passed into `run_task(env=…)`. **Vault is run with `SEND__STORAGE_MODE=memory` on Fargate** (a hard Q1/Q6 decision in the spec) — i.e. the production vault is *already* treated as ephemeral-per-task, not a long-lived disk store.

**"Vault capabilities" — what it concretely means in THIS repo.** Two distinct things share the word "vault":

1. **The Vault App container** (`sg-send-vault`, the SG/Send vault product) — deployed via VAF/Fargate as above. Stateful product, externally reachable, the thing humans log into.
2. **The in-process vault primitives** (`sg_compute/vault/` — `Vault__Spec__Writer`, `Routes__Vault__Spec` mounted at `/api/vault` on `Fast_API__Compute`) — a Type_Safe write-receipt API with an **in-memory dict backing store today; real vault I/O deferred to v0.3** (reality `vault/index.md` lines 43-47). Plus the `sg vault` / `sg credentials` CLI surfaces and OS-keyring storage (`sg-compute/index.md` lines 55-101).

These are very different deployability profiles and the brief keeps them separate.

### 1.5 IAM / lifecycle precedents relevant to Lambda+vault

- `Vault_App__Stop__Policy__Template` — tag-conditioned `ec2:Stop/StartInstances` on `StackType=vault-app` (`aws/iam/service/templates/`). Lifecycle/permission model for the EC2-era vault.
- `Waker__Policy__Template` — the policy shape for the waker Lambda.
- VAF setup manages an **ECS task execution role** per cluster (`Schema__VAF__Cluster__Config.execution_role_arn / task_role_arn`).
- `sp-playwright-cli-lambda` role has 5 inline `sp-cli-*` policies (`infra/index.md` line 64) — the existing model for a Lambda execution role in this repo.

---

## 2. Container-image Lambda vs ZIP Lambda — decision table for THIS codebase

| Dimension | ZIP package Lambda | Container-image Lambda | Verdict for SG/API |
|-----------|--------------------|------------------------|--------------------|
| **Artefact size cap** | 250 MB **unzipped** (incl. layers) | **10 GB** image | The noble Playwright base alone (Chromium + libs) is well over 1 GB. **ZIP is a non-starter for SG/API. Image required.** |
| **Chromium dependency** | Would need Chromium + ~40 shared libs bundled into the zip. Not feasible at 250 MB; no managed layer for it. | The `mcr.microsoft.com/playwright/python:v1.58.0-noble` base **already contains** Chromium and system deps — reused as-is. | **Decisive in favour of image.** This single fact kills zip for SG/API. |
| **Vault publish/admin/edge Lambdas (no browser)** | Already deploy fine as **ZIP + S3 combined-deps** (existing precedent). | Possible but pointless — they are small. | **Keep those on ZIP.** Do not migrate them. |
| **In-process vault primitives (`/api/vault`)** | Tiny; trivially fits zip. | Trivially fits image. | Either; rides along with whichever app hosts them. |
| **FastAPI HTTP translation** | **Mangum** (the repo's actual precedent: waker/admin/edge all use Mangum via `Serverless__Fast_API`). | **AWS Lambda Web Adapter** (LWA) — run uvicorn unmodified on :8000, LWA bridges API GW/Function URL ↔ HTTP. The parity stub `lambda_handler.py` is already shaped for this (uvicorn on :8000). | For an **image**, **LWA is the cleaner fit** (no Mangum wrapper, the container runs the same uvicorn it runs on EC2/Fargate — preserves "one image, many targets"). For a zip, Mangum. Since we're forced to image, **LWA**. |
| **Base image** | n/a | Microsoft Playwright noble (already pinned + build-guarded in the Dockerfile). LWA added as a `COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter` layer **(PROPOSED — not in the current Dockerfile)**. | Image; minimal Dockerfile delta. |
| **Cold start** | Fast for small zips (waker is tiny). | **Slow for big images** — a >1 GB Chromium image cold-starts in the multi-second range; first Chromium launch adds more. Lambda SnapStart does not cover Python container images. | **Real risk for SG/API.** Acceptable for low-QPS / async screenshot work; bad for latency-sensitive synchronous calls. Mitigate with provisioned concurrency (costs money, erodes the Lambda economics). |
| **Per-invocation hard cap** | 15 min | 15 min | **Same.** Fine for one-shot browser steps; **fatal for any long-running/stateful vault session.** |
| **/tmp & memory** | up to 10 GB /tmp, up to 10 GB RAM | same | Chromium is RAM-hungry; size the function ≥2 GB. Current zip defaults (256 MB) are far too small for a browser. |
| **Build/CI pipeline** | `pip`-build a deps zip + code zip → S3/inline (existing `Lambda__Deployer`). | `docker build` → **push to ECR** → `create_function(PackageType='Image', Code={'ImageUri'})`. ECR push tooling **partially exists** (`Create_Image_ECR`, `Vault_App__Fargate__Image__Mirror`) but the **image-Lambda create/update branch does NOT exist** and must be built. | Image needs new build path; ECR seam reusable. |
| **Reuse of existing tooling** | `Lambda__Deployer` works as-is. | Needs a new deployer branch/class + a new runtime/package-type enum + a Dockerfile.lambda. | Image = more new code, but bounded. |

### Recommendation (Section 2)

**For SG/API: container-image Lambda is the only viable Lambda option — ZIP is categorically impossible because of the 250 MB unzipped cap vs the >1 GB Chromium base image.** This is not a close call; the Chromium dependency alone decides it. Pair the image with the **AWS Lambda Web Adapter** (not Mangum) so the same uvicorn-on-:8000 container runs on Lambda, EC2, and Fargate unchanged — preserving the "one image, many targets" guarantee.

**For the small non-browser Lambdas (vault-publish waker/admin, edge waker): leave them on ZIP + Mangum.** They have no Chromium, they are tiny, and the existing zip tooling already serves them. Do not "containerise for consistency."

**For the stateful Vault App product (`sg-send-vault`): do NOT move it to Lambda.** Keep it on Fargate (VAF). See §3.4.

---

## 3. Proposed architecture

> **PROPOSED — does not exist yet.** None of the classes, Dockerfiles, or CLI verbs in this section are in the repo today. They are a design, scoped against existing seams.

### 3.1 Shape A — SG/API as a container-image Lambda (recommended primary)

```
ECR repo: sg-playwright-lambda            (NEW — separate from the Docker Hub image)
  └─ image: noble Playwright base
            + COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.x /lambda-adapter /opt/extensions/
            + sg_compute / sg_compute_specs / capabilities.json / version   (same COPY block as today)
            + ENV  AWS_LWA_PORT=8000  AWS_LAMBDA_EXEC_WRAPPER=...            (LWA wiring)
            + CMD  python3 -m sg_compute_specs.playwright.core.fast_api.lambda_handler   (uvicorn :8000, unchanged)

Lambda function: sg-playwright-service     (PackageType=Image, x86_64)
  ├─ MemorySize: 2048–3008 MB              (Chromium needs RAM; 256 MB default is wrong)
  ├─ Timeout:    300 s                     (one-shot browser steps; well under the 15-min cap)
  ├─ Execution role: sg-playwright-lambda  (logs + optional vault-secret read)
  └─ Invoke surface: Lambda Function URL (AuthType=NONE) + app-layer API-key middleware
                     — same pattern as sp-playwright-cli-lambda today.
```

- **LWA vs Mangum here:** use **LWA** so `lambda_handler.py` (already uvicorn-on-:8000) runs verbatim. Mangum would force a second handler shape and break the single-entrypoint story. CLAUDE.md's "LWA 1.0.0" line — though stale for the current Docker-Hub reality — is the right choice *for this image-Lambda*.
- **`/admin/*` + 16 direct endpoints** ride along unchanged; FastAPI is the same app object.
- **API Gateway vs Function URL:** **Function URL** (cheaper, simpler, matches the `sp-playwright-cli-lambda` precedent: AuthType=NONE + app-layer API-key middleware). Add API Gateway only if you need WAF/usage-plans/custom-domain features the Function URL lacks (CloudFront in front already gives custom domain today).

### 3.2 Vault *capabilities* in the same image

The **in-process vault primitives** (`/api/vault`, `Vault__Spec__Writer`) are pure Python and already mount on the FastAPI app — they ride inside Shape A for free **if** that app is `Fast_API__Compute` (which hosts `/api/vault`) rather than the narrower `Fast_API__Playwright__Service`. **Decision needed (open question Q1):** which FastAPI app does the Lambda boot? If the goal is "SG/API + vault capabilities in one Lambda," the entrypoint should boot the composition that includes both route trees. Today `Vault__Spec__Writer` is **in-memory only** (real I/O deferred to v0.3), so in Lambda it would be **per-invocation ephemeral** unless backed by a real store — see §5.

### 3.3 How the container gets vault keys at runtime in Lambda

Three options, in order of preference:

1. **Lambda environment variables** (mirror the current Fargate model). `Vault_App__Fargate__Spec.env_for_run` already passes `SEND__ACCESS_TOKEN` / `SEND__SEED_VAULT_KEYS` as task env. Lambda env vars are the direct analogue. Simplest; **but Lambda env vars are visible in the console and not rotated** — acceptable for a short-lived access token, weak for long-lived secrets. Honours CLAUDE.md rule 12/13 only if the values come from CI secrets at deploy time, never committed.
2. **AWS Secrets Manager / SSM Parameter Store, read at cold start** via `osbot-aws` (never boto3 directly — CLAUDE.md rule). The execution role gets a tag-scoped `secretsmanager:GetSecretValue`. Cleaner rotation story; adds a cold-start call. **No code for this exists yet (PROPOSED).** Note the repo already uses SSM for the vault-publish slug registry (`sg-compute/index.md`), so the SSM seam is familiar.
3. **The OS-keyring `Credentials__Store`** (`sg.vault.*` namespace) is **laptop/dev only** — there is no keyring in Lambda. **Not applicable at runtime in Lambda;** it is a developer-machine convenience.

**Recommendation:** env vars for the short-lived access token (matches Fargate), Secrets Manager via `osbot-aws` for anything long-lived. Both keep keys out of Git.

### 3.4 What does NOT fit Lambda — be explicit

- **The stateful Vault App product (`sg-send-vault`).** It is a long-running, externally-addressable service with a data volume and (in compose) disk persistence. Lambda's **15-minute hard cap** and request/response model make it unsuitable as the vault *server*. **Keep it on Fargate (VAF).** Even though Fargate runs it as `STORAGE_MODE=memory` today, it is still a *persistent task* for the life of a session — that is the part Lambda cannot replicate.
- **The mitmproxy sidecar.** Explicitly noted unsuitable for Lambda: "tunnels + CONNECT semantics don't survive the Lambda Function URL adapter" (`Docker__Agent_Mitmproxy__Base.py:5-7`). Stays on EC2.
- **`host-plane`** manages containers via the Docker socket — meaningless in Lambda. Stays on EC2/Fargate.
- **Long browser sequences** approaching 15 min — must stay on EC2/Fargate.

So the honest target is: **SG/API (one-shot browser + screenshot + sequence endpoints) + the in-process vault primitives → container-image Lambda. The Vault App server stays on Fargate.** A "single Lambda for everything including the vault server" is **not architecturally sound** and the brief recommends against it.

---

## 4. Migration path / phases

All phases reuse existing seams where possible and follow one-class-per-file + Type_Safe + `osbot-aws` (no boto3) conventions. **Every item below is PROPOSED.**

**Phase 0 — Decide scope (human, Dinis).** Confirm: (a) image-Lambda is for SG/API + in-process vault primitives only; (b) Vault App server stays Fargate; (c) LWA over Mangum; (d) Function URL over API Gateway; (e) which FastAPI composition boots (Q1).

**Phase 1 — Container-image Lambda support in the deployer (new code).**
- Add `Enum__Lambda__Package_Type` (`ZIP` / `IMAGE`) — new enum class (no Literals).
- Extend `Schema__Lambda__Deploy__Request` with an optional `image_uri` + `package_type` (kept additive; zip default unchanged).
- Add an **image branch** to `Lambda__Deployer` (or a sibling `Lambda__Image__Deployer`): `create_function(PackageType='Image', Code={'ImageUri': …})` / `update_function_code(ImageUri=…)`. This is the single missing capability that blocks everything.
- New CLI verb option `--image-uri` on `sg aws lambda <name> deploy` (mutation-gated as today).

**Phase 2 — The Lambda image build (new Dockerfile + build path).**
- `sg_compute_specs/playwright/Dockerfile.lambda` (or a build arg on the existing one) layering the LWA extension onto the noble base. Reuse the existing COPY/requirements/build-guard block verbatim.
- Reuse `Create_Image_ECR` (osbot-aws, already a dependency) or the `Vault_App__Fargate__Image__Mirror` pattern to build+push to a **new ECR repo `sg-playwright-lambda`**. (The image-mirror class mirrors an existing image; for a *built* image use `Create_Image_ECR` as the mitmproxy helper does.)
- CI: a path-gated job analogous to `build-playwright-image`, but pushing the LWA-flavoured image to ECR (the Docker Hub job stays for EC2/Fargate).

**Phase 3 — IAM + invoke surface.**
- New execution role `sg-playwright-lambda` (logs + optional Secrets-Manager/SSM read), built with the existing `Schema__IAM__Policy` / template pattern (cf. `Vault_App__Stop__Policy__Template`).
- Function URL (AuthType=NONE) + the existing API-key middleware. Reuse the two-statement Function-URL permission fix noted in CLAUDE.md (the documented boto3 carve-out).

**Phase 4 — Vault secret wiring.**
- Env-var pass-through for `SEND__ACCESS_TOKEN` (mirror `env_for_run`); optional Secrets-Manager read via `osbot-aws` for long-lived keys.

**Phase 5 — Deploy-via-pytest + capability profile.**
- Numbered deploy tests (`test_1__create_lambda`, `test_2__invoke__health_info`, …) gated on real AWS + `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`.
- Add a `lambda-container` capability profile to `Capability__Detector` so the deployment matrix stays truthful (Architect owns this per ROLE.md).

**Reused as-is:** ECR mirror/build seam, IAM schema/template pattern, Function-URL permission fix, the uvicorn `lambda_handler.py`, the API-key middleware, the deploy-via-pytest harness.
**Must be built:** the image-Lambda deploy branch, the package-type enum, the LWA Dockerfile layer, the ECR repo + CI job, the execution role, the capability profile.

---

## 5. Open questions & risks

| # | Item | Risk / note |
|---|------|-------------|
| Q1 | **Which FastAPI app boots in the Lambda?** `Fast_API__Playwright__Service` (16 endpoints, no `/api/vault`) or `Fast_API__Compute` (hosts `/api/vault` + the legacy SP-CLI mount)? "SG/API + vault capabilities in one Lambda" implies the latter. **Blocks Phase 0.** | Architecture-defining; pick before any build. |
| Q2 | **Cold start for a >1 GB Chromium image.** Multi-second init + first-Chromium-launch overhead. | High for latency-sensitive sync calls. Mitigation = provisioned concurrency (costs, erodes Lambda economics) or accept async/low-QPS use only. |
| Q3 | **Vault key handling in Lambda.** Env vars (visible, unrotated) vs Secrets Manager (cold-start call, new code). | Medium. CLAUDE.md rules 12/13: keys must come from CI secrets/Secrets Manager, never Git. No Secrets-Manager read code exists yet. |
| Q4 | **In-process vault store is in-memory only (v0.3 deferred).** In Lambda each invocation is a fresh sandbox → vault writes vanish between invocations. | High if anyone expects `/api/vault` to persist. Needs a real backing store (S3/DDB) before Lambda hosting is meaningful for writes. |
| Q5 | **Statefulness of the Vault App server.** 15-min cap + no addressable long-lived process. | **Decided:** keep `sg-send-vault` on Fargate. Do not Lambda-host the vault server. |
| Q6 | **Browser-in-Lambda feasibility.** Chromium runs in Lambda (proven pattern industry-wide) but needs `--no-sandbox`, ≥2 GB RAM, headless, and `/tmp` for user-data-dir. The noble base + sync Playwright should work; **unverified in this repo** (the LWA path was retired before this was ever exercised on the container-Lambda). | Medium. Prove with a Phase-5 deploy test before committing. |
| Q7 | **Cost model.** Fargate always-on (per-second while a task runs) vs Lambda per-invocation (per-ms + provisioned-concurrency if used). | For bursty/low-volume screenshot work, Lambda is cheaper. For steady load or where cold start forces provisioned concurrency, Fargate may win. Model against expected QPS before migrating SG/API off EC2/Fargate. |
| Q8 | **CLAUDE.md is stale** ("LWA 1.0.0", "Lambda Web Adapter — not Mangum", "Lambda" as a live target). | Low but real: a Dev reading CLAUDE.md will think LWA-on-Lambda already works for SG/API. **Recommend a Librarian/Historian note** reconciling CLAUDE.md with the v0.2.11 retirement and this brief. |

---

## 6. Bottom line

- **SG/API on Lambda ⇒ container image, full stop.** ZIP is impossible (250 MB unzipped vs a >1 GB Chromium base). The Chromium dependency alone decides it. Pair with **LWA** (not Mangum) to keep "one image, many targets."
- **The repo has NO container-image Lambda code today** — neither a deployer branch, an enum, nor a Dockerfile. The zip deployer (`Lambda__Deployer`) and the ECR seams exist and are reusable, but the image-Lambda create/update path must be built (Phase 1).
- **Leave the small non-browser Lambdas on ZIP+Mangum** (waker/admin/edge) and **leave the stateful Vault App server on Fargate.** Lambda's 15-min cap and statelessness rule it out as the vault *server*; only SG/API's one-shot endpoints + the in-process vault primitives belong on the image-Lambda.
- **Biggest unknowns before committing:** cold start for the Chromium image (Q2), which FastAPI app boots (Q1), and the fact that the in-process vault store is in-memory-only today (Q4).
