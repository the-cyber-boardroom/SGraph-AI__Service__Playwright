---
date: 2026-05-17
status: COMPLETE
area: sg_compute_specs/vault_publish + sgraph_ai_service_playwright__cli/aws/{cf,lambda_}
slice: vault-publish-spec v0.2.23 — subdomain routing cold path (P1b through P2d)
branch: claude/review-vault-publish-spec-FT9hq
merged_to_dev: false
---

# Session Debrief — vault-publish spec v0.2.23

## 1. Header

**Date:** 2026-05-17
**Status:** COMPLETE
**Versions shipped:** `sg_compute_specs/vault_publish/version` (no version file bump; version is in MANIFEST)
**Branch:** `claude/review-vault-publish-spec-FT9hq` — **not yet merged to dev**

| Commit | One-line |
|--------|----------|
| `a8c272c` | feat(P1b): vault-publish scaffold — slug primitives, registry, service, CLI |
| `da82018` | feat(P2a): sg aws cf CloudFront primitive — create/disable/delete/wait |
| `1e78cf1` | feat(P2b): sg aws lambda primitive — deploy/list/delete, Function URL CRUD |
| `6195332` | feat(P2c): vault-publish Waker Lambda handler |
| `432ba5d` | feat(P2d): vault-publish bootstrap — Waker Lambda + CloudFront deployment |

(P1a was committed in the prior session as `a5de0b1`.)

---

## 2. TL;DR for the next agent

1. **All 5 phases of the vault-publish-spec v0.2.23 plan are COMPLETE.** The cold path from `<slug>.aws.sg-labs.app` → CloudFront → Waker Lambda → EC2 cold-start is fully implemented and tested.
2. **Branch is NOT yet merged to dev.** Merge before starting any new session. No blockers — all 201+ tests pass.
3. **No Route53 wiring yet.** The `bootstrap` command creates the Lambda + CF distribution but does NOT create the wildcard Route53 ALIAS record. That is the immediate follow-up if DNS routing is needed.
4. **No SSM persistence in bootstrap.** Bootstrap stores nothing in SSM — the distribution ID, lambda name, and waker URL are returned in the response only. An SSM store step is the next natural follow-up.
5. **`Slug__Routing__Lookup` is listed as EXISTS in the service layer but is not wired to the Waker.** `Endpoint__Resolver__EC2` does EC2 describe-instances directly — `Slug__Routing__Lookup` is available if a registry-first approach is preferred later.

---

## 3. What was done

### P1b — vault-publish scaffold (`a8c272c`)
- `sg_compute_specs/vault_publish/` — 31 files covering schema layer (primitives, enums, collections, schemas), service layer (`Slug__Registry` / `Slug__Validator` / `Vault_Publish__Service`), CLI (`Cli__Vault_Publish`), and manifest.
- `sg_compute.cli.Cli__SG` updated to mount `vault-publish` app under `vp` alias.
- 47 unit tests (registry, validator, service end-to-end) — all in-memory, SSM faked via factory seam.

### P2a — CloudFront primitive (`da82018`)
- `sgraph_ai_service_playwright__cli/aws/cf/` — 16 files: enums, primitives, collections, schemas, service (builder + AWS client), CLI.
- `CloudFront__AWS__Client` sole boto3 boundary. `EXCEPTION` comment per CLAUDE.md rule.
- `CloudFront__AWS__Client__In_Memory` in `tests/unit/...` — dict-backed, monotonic counter IDs.
- `sg aws cf` commands: `distributions list/show/create/disable/delete/wait`.
- 36 unit tests.

### P2b — Lambda primitive (`1e78cf1`)
- `sgraph_ai_service_playwright__cli/aws/lambda_/` — 15 files: enums, primitives, collections, schemas, service (AWS client + deployer), CLI.
- `Lambda__Deployer` zips a folder to bytes and creates/updates the Lambda.
- `Lambda__AWS__Client__In_Memory` + `Lambda__Deployer__In_Memory` test helpers.
- `sg aws lambda deploy/list/delete` + `url create/show/delete`.
- 16 unit tests.

### P2c — Waker Lambda (`6195332`)
- `sg_compute_specs/vault_publish/waker/` — 12 files: schemas (Enum__Instance__State, Schema__Endpoint__Resolution, Schema__Waker__Request_Context), `Slug__From_Host`, abstract `Endpoint__Resolver` + concrete `Endpoint__Resolver__EC2`, `Warming__Page`, `Endpoint__Proxy`, `Waker__Handler`, `Fast_API__Waker`, `lambda_entry.py`.
- State machine in `Waker__Handler`: STOPPED→start+202, PENDING/STOPPING→202, RUNNING+healthy→proxy, UNKNOWN→404.
- FastAPI app with catch-all `/{path:path}` + `GET /health`. LWA pattern (no Mangum).
- 31 unit tests (10 slug-parse + 9 warming-page + 12 handler states).

### P2d — Bootstrap (`432ba5d`)
- `Schema__Vault_Publish__Bootstrap__Request` (cert_arn / zone / role_arn; defaults to wildcard ACM cert + `aws.sg-labs.app`).
- `Schema__Vault_Publish__Bootstrap__Response` (distribution_id / domain_name / lambda_name / waker_url / zone / created / message / elapsed_ms).
- `Vault_Publish__Service.bootstrap()`: deploy Lambda via `Lambda__Deployer`, create Function URL via `Lambda__AWS__Client`, extract domain, create CF distribution. Three new factory seams: `_cf_client_factory / _deployer_factory / _lambda_client_factory`.
- `Cli__Vault_Publish.bootstrap` replaced PROPOSED stub with real Typer command.
- 24 unit tests with inline in-memory fakes (matching the pattern in `test_Waker__Handler.py`).

---

## 4. Failure classification

**Good failure — `list` annotation rejected by Type_Safe (P2a).**
`aliases: list = []` in `Schema__CF__Create__Request` caused `ValueError: variable 'aliases' is defined as type '<class 'list'>' which is not supported by Type_Safe`. Caught immediately by constructor call in a test. Fixed by creating `List__CF__Alias(Type_Safe__List)` with `expected_type = str`. This reinforced the project-wide rule: collection attributes must use `Type_Safe__List` subclasses, never raw `list`.

**Good failure — timestamp-based fake ID collision (P2a).**
`_Fake_CF_Client` generated IDs from `int(time.time() * 1000) % 10**13`. Two creates in the same millisecond got the same ID, causing `test_after_two_creates_returns_two` to fail. Fixed by using a class-level monotonic counter (`_counter += 1`). Caught by tests before merge.

**Good failure — `status_codes: list` on `CloudFront__Origin__Failover__Builder` (P2a).**
Same `list`-annotation issue. Fixed by removing the class attribute entirely and accepting `status_codes` as a method parameter on `build(self, status_codes=None)`.

No bad failures this session.

---

## 5. Lessons learned

**Type_Safe list attributes:** `Type_Safe` supports `bool, int, float, complex, str, bytes, NoneType, EnumType, type` plus Type_Safe subclasses. Raw `list`, `dict`, `tuple` are rejected. The supported pattern is `class MyList(Type_Safe__List): expected_type = SomeType` — then use `MyList` as the attribute type annotation. Passing a plain Python list in the constructor works fine when the field is `MyList`-typed.

**boto3 exception pattern:** When osbot_aws doesn't cover an operation (CloudFront, Lambda), use boto3 directly with a `# EXCEPTION — see module header` comment. The module header documents why.

**In-memory Lambda deployer:** `Lambda__Deployer` has its own `client()` method returning a boto3 client. The in-memory subclass `Lambda__Deployer__In_Memory` overrides both `client()` (returning the fake's internal `_fake`) and `_zip_folder()` (returning `b'FAKE_ZIP'`). These two seams cover everything needed for unit testing deploy.

**Factory seam pattern:** All AWS clients use `Optional[Callable]` factory seams on `Type_Safe` classes. Calling `_resolver_factory()` if not None else instantiate the real class is the universal pattern. Tests inject fakes via `lambda: fake_instance`. No mocks needed.

**Waker test pattern:** Large state machine (5 paths). Instead of importing test helpers from distant paths, define inline classes extending the base class directly in the test file — `class _Resolution__Fixed(Endpoint__Resolver)`. This avoids import path fragility across package boundaries.

**`Safe_Str__Lambda__Url` regex requires trailing slash:** `^https://[a-z0-9]+\.lambda-url\.[a-z0-9-]+\.on\.aws/$`. The fake URL must end with `/`. When extracting the CF origin domain, strip with `.removeprefix('https://').rstrip('/')`.

---

## 6. Files changed this session

### New files — sg_compute_specs/vault_publish/ (P1b + P2c + P2d)
- `__init__.py`, `manifest.py`, `version`
- `schemas/` — Safe_Str__Slug, Safe_Str__Vault__Key, Enum__Slug__Error_Code, Enum__Vault_Publish__State, List__Slug, List__Schema__Vault_Publish__Entry, Schema__Vault_Publish__Entry, Schema__Vault_Publish__Register__{Request,Response}, Schema__Vault_Publish__Status__Response, Schema__Vault_Publish__Unpublish__Response, Schema__Vault_Publish__List__Response, **Schema__Vault_Publish__Bootstrap__{Request,Response}** (P2d)
- `service/` — Slug__Registry, Slug__Validator, Slug__Routing__Lookup, Vault_Publish__Service, reserved/Reserved__Slugs
- `cli/Cli__Vault_Publish.py`
- `waker/` — Slug__From_Host, Endpoint__Resolver, Endpoint__Resolver__EC2, Warming__Page, Endpoint__Proxy, Waker__Handler, Fast_API__Waker, lambda_entry.py, schemas/(Enum__Instance__State, Schema__Endpoint__Resolution, Schema__Waker__Request_Context)
- `tests/` — test_Safe_Str__Slug, test_Slug__Registry, test_Slug__Validator, test_Vault_Publish__Service, tests/waker/(test_Slug__From_Host, test_Warming__Page, test_Waker__Handler), **test_Vault_Publish__Service__bootstrap** (P2d)

### New files — sgraph_ai_service_playwright__cli/aws/cf/ (P2a)
- Full sub-package: enums/(Enum__CF__Distribution__Status, Enum__CF__Price__Class, Enum__CF__Origin__Protocol), primitives/(Safe_Str__CF__Distribution_Id, Safe_Str__CF__Domain_Name, Safe_Str__Cert__Arn, Safe_Str__CF__Origin_Id), collections/(List__CF__Alias, List__Schema__CF__Distribution, List__Schema__CF__Origin), schemas/(Schema__CF__Distribution, Schema__CF__Create__Request, Schema__CF__Create__Response, Schema__CF__Action__Response, Schema__CF__Origin), service/(CloudFront__Distribution__Builder, CloudFront__Origin__Failover__Builder, CloudFront__AWS__Client), cli/Cli__Cf.py
- Test helper: `tests/unit/.../CloudFront__AWS__Client__In_Memory.py`

### New files — sgraph_ai_service_playwright__cli/aws/lambda_/ (P2b)
- Full sub-package: enums/(Enum__Lambda__Url__Auth_Type, Enum__Lambda__Runtime, Enum__Lambda__State), primitives/(Safe_Str__Lambda__Name, Safe_Str__Lambda__Arn, Safe_Str__Lambda__Url), collections/List__Schema__Lambda__Function, schemas/(Schema__Lambda__Function, Schema__Lambda__Deploy__{Request,Response}, Schema__Lambda__Url__Info, Schema__Lambda__Action__Response), service/(Lambda__AWS__Client, Lambda__Deployer), cli/Cli__Lambda.py
- Test helper: `tests/unit/.../Lambda__AWS__Client__In_Memory.py` (includes `Lambda__Deployer__In_Memory`)

### Modified files
- `sg_compute/cli/Cli__SG.py` — mount vault-publish app under `sg vp` alias
- `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` — mount `cf_app` + `lambda_app`
- `sg_compute_specs/vault_app/service/Vault_App__Service.py` — P1a stop/start/DNS-leak fix (prior session)
- `sg_compute_specs/vault_publish/service/Vault_Publish__Service.py` — P2d: 3 factory seams + bootstrap()
- `sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py` — P2d: real bootstrap command
- `team/roles/librarian/reality/sg-compute/index.md` — this session's reality update

---

## 7. Test status

| Suite | Count | Status |
|-------|-------|--------|
| `sg_compute_specs/vault_publish/tests/` | 102 | ALL PASS |
| `tests/unit/.../aws/cf/` | 36 | ALL PASS |
| `tests/unit/.../aws/lambda_/` | 16 | ALL PASS |
| Full vault_publish suite | 102 | ALL PASS |

No pre-existing failures introduced. No integration tests (require AWS credentials).

---

## 8. Open questions

1. **Route53 wildcard ALIAS record** — should `bootstrap` also create `*.aws.sg-labs.app` → CF distribution ALIAS record? Requires `Route53__AWS__Client.upsert_a_alias_record(zone_id_or_name, name, alias_dns_name, alias_zone_id)`. Recommended: yes, as a follow-up slice. CloudFront hosted zone ID is always `Z2FDTNDATAQYW2`.
2. **SSM persistence of bootstrap state** — should distribution ID, lambda name, and waker URL be stored in SSM? Recommended: yes, as a follow-up slice, using keys like `/sg-compute/vault-publish/bootstrap/{cloudfront-distribution-id,lambda-name,waker-function-url}`.
3. **Lambda execution role** — `bootstrap` requires `role_arn`. Currently passed as a flag with empty default (deploy will fail without it). Should it be read from SSM/env fallback? Recommended: add `os.environ.get('SG_AWS__LAMBDA__ROLE_ARN', '')` fallback in `bootstrap()`.

---

## 9. Follow-ups

### Must-do before merging this branch
- [ ] Confirm all 102 + 52 tests pass on a clean run: `python -m pytest sg_compute_specs/vault_publish/ tests/unit/sgraph_ai_service_playwright__cli/aws/ -q`
- [ ] Review `Vault_Publish__Service.bootstrap()` — verify the waker folder path computation is correct when deployed to Lambda (`os.path.dirname(__file__)` relative path)
- [ ] Merge branch to dev

### Next big slice
- **Route53 + SSM wiring for bootstrap** — one slice: add R53 ALIAS creation + SSM persistence to `Vault_Publish__Service.bootstrap()`. The R53 client (`osbot_aws.aws.route_53.Route_53`) already has `upsert_a_alias_record()`. Write the plan as `team/comms/plans/v0.2.24__vault-publish-route53-ssm.md`.

### Smaller items / opportunistic
- `Slug__Routing__Lookup` is wired but not used. Wire it as a fast-path in `Waker__Handler` before EC2 describe-instances call.
- Add `sg vp waker` sub-commands (info / logs / invoke) — was listed in the original spec but deferred.
- The `_Fake_CF_Client._counter` is class-level and shared across test classes. If tests ever run in parallel, this could produce non-deterministic IDs. Consider resetting in `setup_method`.

---

## 10. Where to start (if continuing this work)

Reading order for a fresh agent:
1. `team/roles/librarian/reality/sg-compute/index.md` — sg_compute_specs/vault_publish/ section (just added)
2. `sg_compute_specs/vault_publish/service/Vault_Publish__Service.py` — the orchestrator; understand the 5 factory seams
3. `sg_compute_specs/vault_publish/waker/Waker__Handler.py` — the state machine
4. `sg_compute_specs/vault_publish/waker/lambda_entry.py` — LWA entrypoint
5. `sgraph_ai_service_playwright__cli/aws/cf/service/CloudFront__AWS__Client.py` — CF boto3 boundary
6. `sgraph_ai_service_playwright__cli/aws/lambda_/service/Lambda__Deployer.py` — Lambda deploy boundary

**Do NOT touch** without deliberate intent:
- `sg_compute_specs/vault_publish/waker/schemas/` — these schemas are the contract for the Waker Lambda
- `sgraph_ai_service_playwright__cli/aws/cf/primitives/Safe_Str__Cert__Arn.py` — regex matches the ACM ARN format exactly

---

## 11. What to take into account next session

- **AWS region split:** CloudFront always uses `us-east-1` (global service). The ACM cert ARN must also be `us-east-1`. Lambda and EC2 use the stack's region (default `eu-west-2`).
- **Mutation guards:** `SG_AWS__CF__ALLOW_MUTATIONS=1` gates CF create/disable/delete. `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` gates Lambda deploy/delete. Without these env vars the CLI commands exit non-zero.
- **LWA pattern:** The Waker Lambda uses AWS Lambda Web Adapter (not Mangum). LWA is injected as an extension layer; the lambda listens on port 8080.
- **Type_Safe__List is `list` AND `Type_Safe__Base`:** Attributes typed as `MyList(Type_Safe__List)` accept plain Python lists in constructors — `MySchema(field=['a','b'])` works. Raw `list` type annotations are rejected by Type_Safe.
- **This branch contains P1a (vault-app stop/start + DNS-leak fix) as well as P1b–P2d.** All work is on `claude/review-vault-publish-spec-FT9hq`.
