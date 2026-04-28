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

### `ec2/service/Ec2__AWS__Client.py` — central EC2 AWS boundary (Phase A steps 3a–3d, 3f, 2026-04-26)

In step 3f, three typer commands (`cmd_list`, `cmd_info`, `cmd_delete`) reduced to thin wrappers over `Ec2__Service`:

- `Schema__Ec2__Instance__Info` gained `instance_type : Safe_Str__Text` (read from the `sg:instance-type` tag with fallback to the AWS-side `instance_type` field).
- `Ec2__Service` gained `delete_all_instances() -> Schema__Ec2__Delete__Response` to support `sp delete --all` without the typer command iterating directly.
- `cmd_info` is now ~40 lines (was ~60+); body = call service, render with new `_render_info()` Tier-2A helper.
- `cmd_delete` is now a thin wrapper that calls either `delete_instance(target)` or `delete_all_instances()`.
- `cmd_list` keeps its inline AMI-source map + launch-time fetch (still needs raw boto3 due to osbot's `LauchTime` typo) but reads instance basics from `Ec2__Service().list_instances()`.
- New shared helper `_resolve_typer_target(target)` handles the "auto-pick when only one instance" UX. The older `_resolve_target` stays in place for the 12 typer commands that still need raw `details`; those reduce in a future slice.

In step 4, the previously CLI-only `sp delete --all` op gets an HTTP route:

- `DELETE /ec2/playwright/delete-all` — calls `service.delete_all_instances()`. Returns `Schema__Ec2__Delete__Response` with empty `target` / `deploy_name` and a populated `terminated_instance_ids`. Route registered in `Routes__Ec2__Playwright.setup_routes()` alongside the other lifecycle routes.
- `Ec2__Service__In_Memory` (the test fixture) gained a matching `delete_all_instances()` override.

Other typer commands (`connect`, `shell`, `exec`, `forward`, `wait`, `screenshot`, `smoke`, `bake-ami`, `wait-ami`, `tag-ami`, etc.) are interactive (SSM session, port-forwarding, screenshots) — they do not naturally fit a stateless HTTP request/response and were not added as routes.

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

### `opensearch/` — `sp os` sister section foundation (Phase B steps 5a–5e, 2026-04-26)

First two slices of the new OpenSearch sister section. Folder name is `opensearch/` (not `os/`) — `os` shadows the Python stdlib `os` module and breaks `import os` inside the package. The typer command alias stays `sp os` / `sp opensearch`.

| File | Role |
|------|------|
| `opensearch/primitives/Safe_Str__OS__Stack__Name.py` | Logical name for an ephemeral OS+Dashboards stack. Same regex as `Safe_Str__Elastic__Stack__Name`. |
| `opensearch/primitives/Safe_Str__OS__Password.py` | Admin password (URL-safe base64, 16-64 chars). Mirrors `Safe_Str__Elastic__Password`. |
| `opensearch/primitives/Safe_Str__IP__Address.py` | Local copy of the IP-address primitive (sister sections stay self-contained; promotion to a shared location is a future cleanup). |
| `opensearch/enums/Enum__OS__Stack__State.py` | Lifecycle state vocabulary (PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN). Mirrors `Enum__Elastic__State`. |
| `opensearch/schemas/Schema__OS__Stack__Create__Request.py` | Create inputs — all fields optional, mirrors elastic create request. |
| `opensearch/schemas/Schema__OS__Stack__Create__Response.py` | Returned once on create; carries the generated `admin_password`, the `dashboards_url`, and the `os_endpoint`. |
| `opensearch/schemas/Schema__OS__Stack__Info.py` | Public view of one stack — never includes `admin_password`. |
| `opensearch/schemas/Schema__OS__Stack__List.py` | Response wrapper for `list_stacks()`. |
| `opensearch/schemas/Schema__OS__Stack__Delete__Response.py` | Empty fields ⇒ route returns 404. |
| `opensearch/schemas/Schema__OS__Health.py` | Cluster + Dashboards health snapshot; `-1` sentinels mark unreachable probes. |
| `opensearch/collections/List__Schema__OS__Stack__Info.py` | Type_Safe__List for the listing response. |
| `opensearch/service/OpenSearch__AWS__Client.py` | Composition shell — declares tag constants + `OS_NAMING`, exposes `sg` / `ami` / `instance` / `tags` slots wired by `setup()`. **Per-concern helpers below live in their own files** (one class per file per CLAUDE.md rule #21) so each can be reviewed and edited in isolation. |
| `opensearch/service/OpenSearch__SG__Helper.py` | `ensure_security_group(region, stack_name, caller_ip)` — idempotent SG create + ingress on Dashboards port 443; `delete_security_group(region, sg_id)`. ASCII-only Description (AWS rejects multi-byte). |
| `opensearch/service/OpenSearch__AMI__Helper.py` | `latest_al2023_ami_id(region)` (raises if none); `latest_healthy_ami_id(region)` filtered by `sg:purpose=opensearch` + `sg:ami-status=healthy` (returns empty string if none). |
| `opensearch/service/OpenSearch__Instance__Helper.py` | `list_stacks(region)` returns `{instance_id: details}` filtered by `sg:purpose=opensearch` + live states; `find_by_stack_name(region, stack_name)`; `terminate_instance(region, instance_id)`. |
| `opensearch/service/OpenSearch__Tags__Builder.py` | Pure mapper — builds the canonical 6-tag list (Name, sg:purpose, sg:section, sg:stack-name, sg:allowed-ip, sg:creator). Creator falls back to 'unknown' when empty. |
| `opensearch/service/OpenSearch__HTTP__Base.py` | Request seam wrapping `requests` with `verify=False` (self-signed cert at boot), Basic auth, scoped urllib3 InsecureRequestWarning suppression. Tests substitute `requests.request` via a recorder. |
| `opensearch/service/OpenSearch__HTTP__Probe.py` | Read-only probes — `cluster_health(base_url, ...)` (returns `{}` on unreachable / non-200 / non-JSON; caller maps to `-1` sentinels in `Schema__OS__Health`); `dashboards_ready(base_url, ...)` (True on 2xx). Composes `OpenSearch__HTTP__Base`. |
| `opensearch/service/Caller__IP__Detector.py` | Fetches caller's public IPv4 from `https://checkip.amazonaws.com`; tests subclass and override `fetch()`. Section-local copy. |
| `opensearch/service/Random__Stack__Name__Generator.py` | `'<adjective>-<scientist>'` generator; pools match the elastic vocabulary by design. |
| `opensearch/service/OpenSearch__Stack__Mapper.py` | Pure mapper: raw boto3 `describe_instances` detail dict → `Schema__OS__Stack__Info`. State enum mapping locked by tests. |
| `opensearch/service/OpenSearch__Service.py` | Tier-1 orchestrator. Exposes `list_stacks(region)`, `get_stack_info(region, stack_name)`, `delete_stack(region, stack_name)`, `health(region, stack_name, username, password)`. Composes the AWS client + HTTP probe + mapper + IP detector + name generator via `setup()`. **`create_stack` lands in step 5f** when the user-data builder is wired. |

101 unit tests across primitives / enums / schemas / collections / AWS helpers / HTTP base + probe / mapper / service / composition. Every AWS- and HTTP-touching class is exercised through real `_Fake_*` subclasses (no mocks); each helper has its own focused test file kept under ~150 lines.

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
