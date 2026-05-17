---
title: "02 — Re-use map: brief concept → existing artefact → action"
file: 02__reuse-map.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
---

# 02 — Re-use map

The brief asks for a lot. Most of it already exists. This file maps each brief concept to the existing code that supplies it (or to the new file that must be created) and chooses one of four actions:

- **REUSE** — import and call as-is, no edits.
- **EXTEND** — add methods / fields to an existing file.
- **REPLACE** — delete an old piece and write a different one (rare).
- **NEW** — net-new file, no prior art.

Action choice is driven by the principle: **maximise REUSE, prefer EXTEND over NEW, never REPLACE unless the old shape is actively wrong.**

---

## 1. Substrate — `sg vault-app`

| Brief concept | Existing artefact | Action |
|---------------|-------------------|--------|
| Create a vault-app stack | `sg_compute_specs/vault_app/service/Vault_App__Service.py::create_stack` (line 79) | REUSE |
| Tag-based stack discovery | `Vault_App__Service.py::list_stacks` (line 179) | REUSE |
| Terminate stack | `Vault_App__Service.py::delete_stack` (line 528) | REUSE |
| Stack info / health | `Vault_App__Service.py::{get_stack_info,health}` | REUSE |
| Per-slug A record (on create) | `Vault_App__Auto_DNS.py` (entire file) | REUSE |
| `Vault_App__Service.stop_stack` | (new method on existing class) | EXTEND `Vault_App__Service.py` |
| `Vault_App__Service.start_stack` | (new method on existing class) | EXTEND `Vault_App__Service.py` |
| `Vault_App__Service._delete_per_slug_a_record` | (private helper composing existing `Route53__AWS__Client.delete_record`) | EXTEND `Vault_App__Service.py` |
| Schemas `Schema__Vault_App__{Stop,Start}__Response` | (no existing) | NEW under `sg_compute_specs/vault_app/schemas/` (one file per class — CLAUDE.md rule #21) |
| `Schema__Vault_App__{Stop,Start}__Request` | (the brief shows these but the existing `Schema__Vault_App__Create__Request` shape suggests in practice stop/start take `region`+`name` as method args, not a schema) | NEW (per brief) — even if minimal, one-class-per-file rule applies |
| CLI verbs `sg vault-app stop / start` | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` (existing Typer app) | EXTEND `Cli__Vault_App.py` |
| User-data idle hook: `shutdown` → `aws ec2 stop-instances` | `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py::render` | EXTEND `Vault_App__User_Data__Builder.py` (small surgical change) |
| `InstanceInitiatedShutdownBehavior='stop'` on launch | `sg_compute_specs/vault_app/service/Vault_App__AWS__Client.py::launch.run_instance` (called from `Vault_App__Service.py:153`) | EXTEND `Vault_App__AWS__Client.py` |
| IAM `ec2:StopInstances` policy on `playwright-ec2` profile | `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py` (around line 177, policy assembly) | EXTEND `Ec2__AWS__Client.py` (NOT vault_app/ — see grounding §1.5) |
| In-memory `Vault_App__AWS__Client__In_Memory` for stop/start tests | (precedent: other `*__In_Memory` siblings under `tests/unit/`) | EXTEND existing in-memory subclass if it exists; else NEW |

---

## 2. DNS layer — `sg aws dns`

| Brief concept | Existing artefact | Action |
|---------------|-------------------|--------|
| Route 53 mutations (upsert, delete, get) | `sgraph_ai_service_playwright__cli/aws/dns/service/Route53__AWS__Client.py` | REUSE (sole boto3 boundary) |
| FQDN → owning zone | `Route53__Zone__Resolver.py` | REUSE (Waker `Slug__From_Host` composes it) |
| EC2 → public IP | `Route53__Instance__Linker.py` | REUSE |
| Smart verification | `Route53__Smart_Verify.py` | REUSE (bootstrap + status verbs) |
| Authoritative / public-resolver checkers | `Route53__{Authoritative,Public_Resolver,Local}__Checker.py` | REUSE |
| `Dig__Runner` (shell-out to dig) | `Route53__Dig__Runner` already in `aws/dns/service/` | REUSE |
| Default zone constant + env var | `Route53__AWS__Client.DEFAULT_ZONE_NAME_FALLBACK` + `SG_AWS__DNS__DEFAULT_ZONE` | REUSE (must not re-derive in vault-publish) |
| `Cli__Dns.py` patterns (mutation gate, sub-typers) | `aws/dns/cli/Cli__Dns.py` (1248 lines) | TEMPLATE — copy shape into `Cli__Cf.py` and `Cli__Lambda.py` |

**Domain-specific Route 53 reuse for `sg-labs.app`** — see `07__domain-strategy.md §5` for the full reuse-map addendum (per-namespace wildcard ALIAS, per-slug A under `<namespace>.sg-labs.app`, TTL policy). Zero new boto3 surface; all reuse of the rows above.

---

## 3. CloudFront — `sg aws cf` (PROPOSED)

All files NEW under `sgraph_ai_service_playwright__cli/aws/cf/` (subfolders: `cli/`, `collections/`, `enums/`, `primitives/`, `schemas/`, `service/`). Pattern mirrors `sg aws dns` exactly.

| Brief concept | New file | Action | CLAUDE.md anchor |
|---------------|----------|--------|------------------|
| `CloudFront__AWS__Client` | `aws/cf/service/CloudFront__AWS__Client.py` | NEW | Sole boto3 boundary; module header notes "EXCEPTION — `osbot_aws.Cloud_Front` only covers list+invalidate" (mirrors `Route53__AWS__Client.py:1-10`) |
| `CloudFront__Distribution__Builder` | `aws/cf/service/CloudFront__Distribution__Builder.py` | NEW | Pure config builder, no boto3, `Type_Safe` |
| `CloudFront__Origin__Failover__Builder` | `aws/cf/service/CloudFront__Origin__Failover__Builder.py` | NEW | Same |
| `Cli__Cf` | `aws/cf/cli/Cli__Cf.py` | NEW | Mutation gate: `SG_AWS__CF__ALLOW_MUTATIONS=1` |
| Schemas (one file each) | `aws/cf/schemas/Schema__CF__*.py` | NEW × ~5 | Rule #21 — one class per file |
| Enums (one file each) | `aws/cf/enums/Enum__CF__*.py` | NEW × 3 | Rule #3 — no Literals |
| Primitives (one file each) | `aws/cf/primitives/Safe_Str__CF__*.py` | NEW × 4 | Rule #2 — no raw `str` attributes |
| Collections (one file each) | `aws/cf/collections/List__Schema__CF__*.py` | NEW × 2 | Rule #21 |
| In-memory client | `tests/unit/sgraph_ai_service_playwright__cli/aws/cf/service/CloudFront__AWS__Client__In_Memory.py` | NEW | No mocks; dict-backed dispatch |
| Mount under `sg aws` | `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` (existing) | EXTEND | One `add_typer(_cf_app, name='cf')` line |

**Estimated ~24 production files + ~6 tests** (matches brief).

---

## 4. Lambda primitive — `sg aws lambda` (PROPOSED)

All NEW under `sgraph_ai_service_playwright__cli/aws/lambda_/`. Note: `lambda_` with trailing underscore because `lambda` is a Python keyword (already-standard convention; the brief acknowledges this in its folder name).

| Brief concept | New file | Action |
|---------------|----------|--------|
| `Lambda__Deployer` (wraps `osbot_aws.Deploy_Lambda`) | `aws/lambda_/service/Lambda__Deployer.py` | NEW |
| `Lambda__AWS__Client` (read paths over `osbot_aws.Lambda`) | `aws/lambda_/service/Lambda__AWS__Client.py` | NEW |
| `Lambda__Url__Manager` (URL CRUD) | `aws/lambda_/service/Lambda__Url__Manager.py` | NEW |
| `Cli__Lambda` | `aws/lambda_/cli/Cli__Lambda.py` | NEW |
| Schemas / enums / primitives / collections (one file each) | `aws/lambda_/{schemas,enums,primitives,collections}/...` | NEW × ~12 |
| In-memory client | `tests/unit/sgraph_ai_service_playwright__cli/aws/lambda_/service/Lambda__AWS__Client__In_Memory.py` | NEW |
| Mount under `sg aws` | `aws/cli/Cli__Aws.py` | EXTEND |

**Estimated ~16 production files + ~5 tests** (matches brief).

---

## 5. `sg_compute_specs/vault_publish/` — the spec (PROPOSED)

All NEW. Folder layout exactly per brief [`04 §1`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md), corrected for CLAUDE.md rules (see `03__delta-from-lab-brief.md` §1 for the diff).

| Brief concept | New file | Action | Source of substance |
|---------------|----------|--------|---------------------|
| `manifest.py` | `sg_compute_specs/vault_publish/manifest.py` | NEW | Brief §9 + `vault_app/manifest.py` exemplar; **use `Enum__Spec__Stability.EXPERIMENTAL`, not `'experimental'`** |
| `version` file | `sg_compute_specs/vault_publish/version` | NEW | Initial `v0.1.0` |
| `Safe_Str__Slug` | `schemas/Safe_Str__Slug.py` | NEW | Brief [`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) (regex `[a-z0-9\-]+`, max 40, strict MATCH); cherry-pick from `claude/review-subdomain-workflow-bRIbm` if Q2 = "cherry-pick" |
| `Safe_Str__Vault__Key` | `schemas/Safe_Str__Vault__Key.py` | NEW | sgit vault-key format (alphanumeric + dash, ~24 chars) |
| `Enum__Slug__Error_Code` | `schemas/Enum__Slug__Error_Code.py` | NEW | 8 reasons per brief |
| `Enum__Vault_Publish__State` | `schemas/Enum__Vault_Publish__State.py` | NEW | UNREGISTERED / STOPPED / PENDING / RUNNING / STOPPING |
| `Reserved__Slugs` | `service/reserved/Reserved__Slugs.py` | NEW | Registry exception per CLAUDE.md rule #21 — frozenset + helper functions live together |
| `Slug__Validator` | `service/Slug__Validator.py` | NEW | Brief [`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md); composes `Safe_Str__Slug` + `Reserved__Slugs` |
| `Slug__Registry` | `service/Slug__Registry.py` | NEW | Uses `osbot_aws.helpers.Parameter` |
| `Slug__Routing__Lookup` | `service/Slug__Routing__Lookup.py` | NEW | Read-only subset for Waker |
| `Vault_Publish__Service` | `service/Vault_Publish__Service.py` | NEW | Extends `Spec__Service__Base` (verified at `sg_compute/core/spec/Spec__Service__Base.py`); composes `Vault_App__Service`, `Route53__AWS__Client`, `CloudFront__AWS__Client`, `Lambda__Deployer`, `Slug__Registry`, `Slug__Validator` |
| Schemas — Register/Unpublish/Status/List/Bootstrap requests + responses | `schemas/Schema__Vault_Publish__*.py` | NEW × ~9 | Rule #21 |
| Collections | `schemas/List__Slug.py`, `schemas/List__Schema__Vault_Publish__Entry.py` | NEW | Rule #21 |
| `Cli__Vault_Publish` | `cli/Cli__Vault_Publish.py` | NEW | Pattern from `Cli__Vault_App.py`; mutation gate `SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1` |
| Mount in `Cli__SG.py` | `sg_compute/cli/Cli__SG.py` (existing) | EXTEND | One `add_typer(name='vault-publish')` + alias `vp` |

---

## 6. Waker — `sg_compute_specs/vault_publish/waker/`

All NEW. The Waker is a tiny FastAPI app deployed as a Lambda via AWS Lambda Web Adapter (matches the repo's existing Lambda pattern — verified via `lambda_handler.py` precedent in `sgraph_ai_service_playwright__cli/`).

| Brief concept | New file | Action | Notes |
|---------------|----------|--------|-------|
| `lambda_entry.py` | `waker/lambda_entry.py` | NEW | FastAPI app; Type_Safe-friendly route handlers; **no Literals** in path-spec defaults |
| `Waker__Handler` | `waker/Waker__Handler.py` | NEW | State machine; composes the resolver / proxy / warming-page / routing-lookup |
| `Endpoint__Resolver` (abstract) | `waker/Endpoint__Resolver.py` | NEW | One class per file; abstract methods `resolve` and `start` |
| `Endpoint__Resolver__EC2` | `waker/Endpoint__Resolver__EC2.py` | NEW | Uses `osbot_aws.aws.ec2.EC2_Instance` directly |
| `Endpoint__Resolver__Fargate` | `waker/Endpoint__Resolver__Fargate.py` | **PROPOSED — does not exist yet** (phase 3) | Out of plan scope |
| `Endpoint__Proxy` | `waker/Endpoint__Proxy.py` | NEW | urllib3 reverse-proxy; respects 6 MB buffered ceiling in phase 2 |
| `Warming__Page` | `waker/Warming__Page.py` | NEW | HTML generator; no inline strings as bare attributes — use `Safe_Str__HTML` style if a class field |
| `Slug__From_Host` | `waker/Slug__From_Host.py` | NEW | Composes `Route53__Zone__Resolver` to identify zone-prefix |
| Lambda execution role | (created at `bootstrap` time via `osbot_aws.aws.iam.IAM_Role_With_Policy`) | REUSE upstream |

---

## 7. Tests

Pattern mirrors `sg_compute_specs/vault_app/tests/` and `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/`. No mocks, no patches (CLAUDE.md testing rule #1).

| Test target | Test file | In-memory dep |
|-------------|-----------|---------------|
| `Slug__Validator` | `tests/test_Slug__Validator.py` | None (pure) |
| `Slug__Registry` | `tests/test_Slug__Registry.py` | `Parameter__In_Memory` (NEW dict-backed subclass of `osbot_aws.helpers.Parameter`) |
| `Vault_Publish__Service` | `tests/test_Vault_Publish__Service.py` | `Vault_App__Service` composed with `Vault_App__AWS__Client__In_Memory` + `Slug__Registry` in-memory + `Route53__AWS__Client__In_Memory` (NEW if it does not exist) |
| `Endpoint__Resolver__EC2` | `tests/waker/test_Endpoint__Resolver__EC2.py` | In-memory `EC2_Instance` subclass (NEW) |
| `Endpoint__Proxy` | `tests/waker/test_Endpoint__Proxy.py` | Tiny inline aiohttp/uvicorn test server (no mocks) |
| `Waker__Handler` | `tests/waker/test_Waker__Handler.py` | All of the above composed |
| `Cli__Vault_Publish` | `tests/test_Cli__Vault_Publish.py` | Golden-file CLI snapshot (matches `Cli__Vault_App` pattern at `vault_app/tests/test_Cli__Vault_App.py`) |
| `Vault_App__Service.{stop,start}_stack` | `vault_app/tests/test_Vault_App__Service__stop_start.py` | `Vault_App__AWS__Client__In_Memory` extended with stop/start state transitions |

See `05__test-strategy.md` for the full strategy + reusable existing fixtures.

---

## 8. Counts

| Bucket | Files |
|--------|-------|
| EXTEND existing files | 5 (`Vault_App__Service.py`, `Vault_App__User_Data__Builder.py`, `Vault_App__AWS__Client.py`, `Cli__Vault_App.py`, `Ec2__AWS__Client.py`) + `Cli__SG.py` + `Cli__Aws.py` = **7** |
| NEW under `sg_compute_specs/vault_publish/` (incl. waker + tests) | **~40** (~30 production + ~8 tests, per brief [`04 §1`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)) |
| NEW under `sgraph_ai_service_playwright__cli/aws/cf/` | **~30** (~24 prod + 6 tests) |
| NEW under `sgraph_ai_service_playwright__cli/aws/lambda_/` | **~21** (~16 prod + 5 tests) |
| Total new files | **~91** |
| Total edited files | **7** |

The total file count is bigger than it looks because of CLAUDE.md rule #21 (one class per file). Most files are under 100 lines.

---

## 9. What is **explicitly NOT** ported / re-used

These are listed because the brief mentions them; the plan declines to carry them forward:

- The v0.2.11 dev-pack's `Vault__Fetcher`, `Manifest__Verifier`, `Manifest__Interpreter`, `Slug__Resolver`, `Instance__Manager`, `Control_Plane__Client`, `Waker__Lambda__Adapter`. The brief itself explicitly deletes these (see [`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)). They do not exist on `dev` anyway. Action: **none** (nothing to delete; record in Historian decision log).
- The `library/dev_packs/v0.2.11__vault-publish/` documentation pack. Brief instructs marking SUPERSEDED. Action: **Historian responsibility, not Dev**.
- Any CloudFront-specific allowlist widening of the JS expression allowlist. The Waker does not run JS; the JS allowlist surface is untouched by this plan.
