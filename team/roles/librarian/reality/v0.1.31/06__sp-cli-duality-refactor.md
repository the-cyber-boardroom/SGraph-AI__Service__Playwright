# Reality — SP CLI / FastAPI Duality Refactor

**Status:** partial — read-only surface + delete mutation implemented.
Other mutation ops (create/backup/restore/dashboard-import/data-export/data-import) and CLI wrappers still PROPOSED.

This file tracks what exists today for the refactor proposed in
[`team/comms/briefs/v0.1.72__sp-cli-fastapi-duality.md`](../../../../comms/briefs/v0.1.72__sp-cli-fastapi-duality.md).
Everything in the brief that is NOT listed below is still PROPOSED.

---

## New top-level package — `sgraph_ai_service_playwright__cli/`

Sibling of `sgraph_ai_service_playwright/` and `agent_mitmproxy/`. Houses the
Type_Safe refactor of the `sp` / `ob` CLI. Nothing under
`sgraph_ai_service_playwright/` was modified. Package version: `v0.0.1`.

### `aws/` — shared AWS infrastructure helpers (Phase A step 1, 2026-04-26)

Single source of truth for naming conventions every sister section needs.

| File | Role |
|------|------|
| `aws/Stack__Naming.py` | Type_Safe class binding a `section_prefix` (e.g. `elastic`, `opensearch`, `prometheus`, `vnc`) once and exposing `aws_name_for_stack()` (Name tag with section prefix; never doubled) + `sg_name_for_stack()` (SG GroupName with `-sg` suffix; never starts with reserved `sg-`). |

The previously-elastic-only module-level functions in `elastic/service/Elastic__AWS__Client.py` (`aws_name_for_stack`, `sg_name_for_stack`) were removed. `Elastic__AWS__Client.py` now declares `ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')` at module level; the 5 prior call sites (2 in `Elastic__AWS__Client`, 2 in `Elastic__Service`, 1 in the in-memory test client) use this shared instance. Future `sp os`, `sp prom`, `sp vnc` sections each get their own `*_NAMING` constant pointing at the same `Stack__Naming` class.

Tests: 9 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/aws/test_Stack__Naming.py` cover prefix-when-missing / no-double-prefix / partial-match-non-counting / per-section-isolation / sg-suffix universality. Plan reference: `team/comms/plans/v0.1.96__playwright-stack-split__02__api-consolidation.md`.

### `ec2/service/Ec2__AWS__Client.py` — central EC2 AWS boundary (Phase A steps 3a–3d, 2026-04-26)

Mirrors the `Elastic__AWS__Client` pattern. Hosts the previously-private helpers that lived in `scripts/provision_ec2.py`:

| Surface | Symbol | Form |
|---------|--------|------|
| Module-level pure helpers | `random_deploy_name`, `get_creator`, `uptime_str`, `instance_tag`, `instance_deploy_name` | Functions; no AWS calls. Naming pools `_ADJECTIVES` / `_SCIENTISTS` live alongside. |
| Module-level constants | `TAG__SERVICE_KEY`, `TAG__SERVICE_VALUE`, `TAG__DEPLOY_NAME_KEY`, `INSTANCE_STATES_LIVE` | Tag/state values used by find / resolve / terminate. |
| Type_Safe class | `Ec2__AWS__Client` | Methods: `ec2()` (single seam, tests override); `find_instances()`; `find_instance_ids()`; `resolve_instance_id(target)`; `terminate_instances(nickname)`. Each EC2 call goes through `self.ec2()` so an in-memory test double can replace the boto3 boundary. |
| AWS context accessors (3b) | `aws_account_id`, `aws_region`, `ecr_registry_host`, `default_playwright_image_uri`, `default_sidecar_image_uri` | Module-level functions over `osbot_aws.AWS_Config`. `PLAYWRIGHT_IMAGE_NAME` + `SIDECAR_IMAGE_NAME` re-exported from the docker base modules. |
| IAM constants + helpers (3c) | `IAM__ROLE_NAME`, `IAM__ECR_READONLY_POLICY_ARN`, `IAM__SSM_CORE_POLICY_ARN`, `IAM__POLICY_ARNS`, `IAM__PROMETHEUS_RW_POLICY_ARN`, `IAM__OBSERVABILITY_POLICY_ARNS`, `IAM__ASSUME_ROLE_SERVICE`, `IAM__PASSROLE_POLICY_NAME`; functions `decode_aws_auth_error(exc)`, `ensure_caller_passrole(account)`, `ensure_instance_profile()` | Module-level. The Console-formatted `_print_auth_error` stays in `provision_ec2.py` (Tier 2A — CLI rendering); `ensure_caller_passrole` no longer prints on auth failure (just raises) — the typer command is now responsible for auth-error formatting. |
| SG + AMI constants (3d) | `SG__NAME`, `SG__DESCRIPTION`, `EC2__AMI_OWNER_AMAZON`, `EC2__AMI_NAME_AL2023`, `EC2__PLAYWRIGHT_PORT`, `EC2__SIDECAR_ADMIN_PORT`, `EC2__BROWSER_INTERNAL_PORT`, `SG_INGRESS_PORTS`, `TAG__AMI_STATUS_KEY` | Module-level. **Bug fix:** `SG__DESCRIPTION` lost its em-dash (AWS rejects non-ASCII `GroupDescription` — see Elastic precedent). Phase C will drop `EC2__BROWSER_INTERNAL_PORT` from `SG_INGRESS_PORTS`. |
| SG + AMI methods (3d) | `Ec2__AWS__Client.ensure_security_group()`, `latest_al2023_ami_id()`, `create_ami(instance_id, name)`, `wait_ami_available(ami_id, timeout=900)`, `tag_ami(ami_id, status)`, `latest_healthy_ami()` | All AWS-touching; go through `self.ec2()` so an in-memory `_Fake_EC2` (with a `_Fake_Boto3_Client`) covers the AMI lifecycle paths. The wrappers in `provision_ec2.py` keep the old `(ec2: EC2)` signatures for callsite stability. |

`scripts/provision_ec2.py` keeps wrapper functions matching the old signatures (`find_instances(ec2: EC2 = None)`, `terminate_instances(ec2: EC2 = None, nickname='')`, etc.) that delegate to a module-level `Ec2__AWS__Client()` instance. The `ec2` parameter is now optional and ignored — callers in `provision_ec2.py` keep working unchanged. These wrappers go away in Phase A step 3f when typer commands become thin wrappers over `Ec2__Service`.

`Ec2__Service` no longer imports lookup helpers from `scripts.provision_ec2` (only the EC2 port constants + tag-name constants remain as imports). Its `list_instances`, `get_instance_info`, `delete_instance`, and `resolve_target` methods now use a `Ec2__AWS__Client` instance via the `aws_client()` seam.

Tests: 24 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py` cover every helper + every class method. AWS calls go through an in-memory `_Fake_EC2` (real subclass, no mocks).

### `image/` — shared Docker image build pipeline (Phase A step 2, 2026-04-26)

Replaces ~70% of duplicated build logic between `Build__Docker__SGraph_AI__Service__Playwright` (Playwright EC2 image) and `Docker__SP__CLI` (SP CLI Lambda image). Both now compose a Type_Safe `Schema__Image__Build__Request` and hand it to the shared service.

| File | Role |
|------|------|
| `image/schemas/Schema__Image__Stage__Item.py` | One file or directory tree to copy into the build context (`source_path`, `target_name`, `is_tree`, `extra_ignore_names`). |
| `image/collections/List__Schema__Image__Stage__Item.py` | Ordered list of stage items (later overrides earlier). |
| `image/collections/List__Str.py` | Typed list of strings (used for `image_tags` + `extra_ignore_names`). |
| `image/schemas/Schema__Image__Build__Request.py` | Inputs: `image_folder` (dockerfile + requirements live here), `image_tag`, `stage_items`, `dockerfile_name='dockerfile'`, `requirements_name='requirements.txt'`, `build_context_prefix`. |
| `image/schemas/Schema__Image__Build__Result.py` | Outputs: `image_id`, `image_tags`, `duration_ms`. |
| `image/service/Image__Build__Service.py` | Orchestrator. Two seams: `stage_build_context()` (pure I/O — exhaustively unit-testable) and `build()` (invokes the docker SDK directly to bypass osbot-docker's @catch wrapper). Default ignore set (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `*.pyc`) is augmented per-item via `extra_ignore_names`. |

Both consumers reduce to thin composers:
- `Build__Docker__SGraph_AI__Service__Playwright.build_docker_image()` returns `Schema__Image__Build__Result`. Composes 3 stage items: `lambda_entry.py` (file), `image_version` (file), `sgraph_ai_service_playwright` (tree).
- `Docker__SP__CLI.build_and_push()` returns the existing dict shape (kept for now: the deploy callers consume `image_uri`/`image_id`/`push` keys). Composes 4 stage items: `sgraph_ai_service_playwright__cli` (tree, `extra_ignore_names=['images']`), `sgraph_ai_service_playwright`, `agent_mitmproxy`, `scripts` (all trees).

Tests: 15 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/image/` cover schema round-trip, default values, stage-context happy path (file + tree + custom-name + extra-ignores), `build()` happy path with an in-memory fake docker client (no daemon required), tempdir-cleanup-on-failure, and ignore-callable composition. Existing consumer tests rewired: `tests/unit/sgraph_ai_service_playwright__cli/deploy/test_Docker__SP__CLI.py` lost its now-redundant `ignore_build_noise` tests (the behaviour moved to `Image__Build__Service`) and gained `test_build_request__has_all_four_source_trees_with_correct_target_names`. The deploy-via-pytest integration test `tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py` updated to assert on `Schema__Image__Build__Result` fields instead of dict keys.

### `observability/` — Tier-1 pure-logic service (read-only surface)

| File | Role |
|------|------|
| `primitives/Safe_Str__Stack__Name.py` | AWS OS-domain-name compliant stack identifier (3-28 chars, lowercase, starts with letter). |
| `primitives/Safe_Str__AWS__Region.py` | AWS region code (MATCH regex). Empty allowed = resolve at runtime. |
| `primitives/Safe_Str__AWS__Endpoint.py` | AWS service endpoint hostname (no scheme). |
| `primitives/Safe_Int__Document__Count.py` | OS doc count; `-1` sentinel = not queried. |
| `enums/Enum__Stack__Component__Status.py` | Normalised lifecycle state across AMP/OS/AMG. |
| `enums/Enum__Stack__Component__Kind.py` | Identifies which AWS service a component represents. |
| `enums/Enum__Component__Delete__Outcome.py` | Per-component delete result code — DELETED / NOT_FOUND / FAILED. |
| `schemas/Schema__Stack__Component__AMP.py` | AMP workspace view. |
| `schemas/Schema__Stack__Component__OpenSearch.py` | OpenSearch domain view. |
| `schemas/Schema__Stack__Component__Grafana.py` | AMG workspace view. |
| `schemas/Schema__Stack__Info.py` | Aggregate stack view (AMP + OS + AMG; each nullable). |
| `schemas/Schema__Stack__List.py` | `list_stacks` response envelope (carries region). |
| `schemas/Schema__Stack__Component__Delete__Result.py` | Per-component delete outcome (kind + outcome + resource_id + error_message). |
| `schemas/Schema__Stack__Delete__Response.py` | `delete_stack` response envelope (name, region, results). |
| `collections/List__Stack__Info.py` | `Type_Safe__List` subclass for `Schema__Stack__Info`. |
| `collections/List__Stack__Component__Delete__Result.py` | `Type_Safe__List` subclass for delete results. |
| `service/Observability__AWS__Client.py` | Isolated boto3 + SigV4 boundary. **Only file in this package that imports boto3.** Methods: `amp_workspaces`, `opensearch_domains`, `amg_workspaces`, `opensearch_document_count`, `amp_delete_workspace`, `opensearch_delete_domain`, `amg_delete_workspace`. |
| `service/Observability__Service.py` | Pure logic: `list_stacks`, `get_stack_info`, `delete_stack`, `resolve_region`. |

### Tests (26 passing, 0 skipped)

| File | Coverage |
|------|----------|
| `tests/unit/sgraph_ai_service_playwright__cli/observability/primitives/test_Safe_Str__Stack__Name.py` | 7 cases — valid/invalid names, length boundaries, auto-init empty. |
| `tests/unit/.../primitives/test_Safe_Str__AWS__Region.py` | 3 cases — valid regions, empty allowed, bad shapes rejected. |
| `tests/unit/.../schemas/test_Schema__Stack__Info.py` | 4 cases — init, composition with components, JSON round-trip, `.obj()` coverage. |
| `tests/unit/.../service/Observability__AWS__Client__In_Memory.py` | In-memory test double (real subclass — no mocks). Fixture fields for listings + delete outcomes. |
| `tests/unit/.../service/test_Observability__Service.py` | 7 cases — list (populated + empty), get (populated / missing / endpoint-less), region resolution. |
| `tests/unit/.../service/test_Observability__Service__delete.py` | 5 cases — all deleted, all missing, partial-missing, forced failure, JSON round-trip. |

---

## What does NOT exist yet (still PROPOSED)

- CLI wrappers in the new package — typer `app` still lives in `scripts/observability.py` and `scripts/provision_ec2.py`. The new `delete_stack` service method is not yet wired to `ob delete`.
- Other mutation operations (`create`, `backup`, `restore`, `dashboard-import`, `data-export`, `data-import`).
- EC2 refactor (`Ec2__Service`) — provision_ec2.py at 2847 lines is untouched.
- FastAPI routes (`/v1/observability/*`).
- GH Actions workflows (`obs-morning.yml`, `obs-evening.yml`).

---

## Known tech-debt items

1. **boto3 usage** — `Observability__AWS__Client` imports boto3 directly, in violation of CLAUDE.md rule 8 (osbot-aws only). No osbot-aws wrapper exists for AMP / OpenSearch / Grafana services yet; the boundary is isolated to one file with a header comment flagging the exception. Swap to osbot-aws when wrappers land.
2. **Safe_Str primitive vs plain-dict key hash mismatch** — `Safe_Str__Stack__Name` has its own `__hash__`; lookups against plain-dict keys need a `str()` normalisation (see `Observability__Service.get_stack_info`). Consider replacing internal `Dict[str, …]` with a `Dict__*` collection subclass keyed by the Safe primitive so the cast disappears.
