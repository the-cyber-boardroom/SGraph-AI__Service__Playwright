# 02 — What Shipped (concrete state per phase)

## Phase A — Shared foundations (8 commits, ✅)

| Step | Commit | What |
|---|---|---|
| 1 | `4ee540c` | `cli/aws/Stack__Naming` — section-aware naming class. Each sister section binds `section_prefix` (`elastic`, `opensearch`, `prometheus`, `vnc`); methods enforce CLAUDE.md rules #14 (no `sg-` prefix) + #15 (no double prefix). |
| 2 | `0162e93` | `cli/image/Image__Build__Service` — shared docker-build pipeline. Reduces ~70% duplication between `Build__Docker__SGraph_AI__Service__Playwright` and `Docker__SP__CLI`. Tests use a real `_Fake_Docker_Client` (no mocks). |
| 3a | `68a6c85` | `Ec2__AWS__Client` — naming + lookup helpers (`random_deploy_name`, `instance_tag`, `find_instances`, `terminate_instances`). |
| 3b | `6ab825d` | AWS context accessors (`aws_account_id`, `aws_region`, `ecr_registry_host`, `default_*_image_uri`). |
| 3c | `5fb8e45` | IAM helpers + 8 ARN/policy constants (`ensure_caller_passrole`, `ensure_instance_profile`). |
| 3d | `166541e` | SG + AMI helpers (`ensure_security_group`, `latest_al2023_ami_id`, AMI lifecycle). Caught + fixed em-dash bug in `SG__DESCRIPTION`. |
| 3f | `cde60c5` | `cmd_list` / `cmd_info` / `cmd_delete` reduced to thin wrappers over `Ec2__Service`. `Schema__Ec2__Instance__Info` gained `instance_type`. |
| 4 | `14cdc51` | `DELETE /ec2/playwright/delete-all` route. |

## Phase B step 5 — `sp os` (10 commits, ✅ functionally complete)

| Step | Commit | What |
|---|---|---|
| 5a | `b0f3805` | Foundation — folder + `Safe_Str__OS__Stack__Name` + `Enum__OS__Stack__State` + `OpenSearch__AWS__Client` skeleton with `OS_NAMING`. **Caught the `os` → `opensearch` rename** (Python stdlib shadowing). |
| 5b | `9a1e04e` | 6 schemas (`Create__Request/Response`, `Info`, `List`, `Delete__Response`, `Health`) + `List__Schema__OS__Stack__Info` + 2 primitives. |
| 5c | `f5dcde7` | 4 small AWS helpers split per concern: `SG__Helper`, `AMI__Helper`, `Instance__Helper`, `Tags__Builder`. Each ~50 lines, each with own ~80-line test file. |
| 5d | `05c0bb7` | `OpenSearch__HTTP__Base` + `OpenSearch__HTTP__Probe` (`cluster_health` / `dashboards_ready`). |
| 5e | `82afd0e` | `OpenSearch__Service` orchestrator (read paths) + `Caller__IP__Detector` + `Random__Stack__Name__Generator` + `Stack__Mapper`. |
| 5f.1 | `363341c` | `OpenSearch__User_Data__Builder` skeleton (placeholders + render contract locked by tests). |
| 5f.2 | `8658520` | `OpenSearch__Compose__Template` (single-node OS + Dashboards; memlock + ulimits; `sg-net`). |
| 5f.3 | `06bf140` | Expanded user-data with Docker install (`dnf`), compose plugin install, `vm.max_map_count` bump, `compose up -d`. |
| 5f.4a | `0a09731` | `OpenSearch__Launch__Helper` — single-purpose `run_instance`, base64 UserData, `MinCount=MaxCount=1`. |
| 5f.4b | `2b21126` | **Wired `create_stack` end-to-end.** Service composes name_gen + ip_detector + ami helper + sg helper + tags builder + compose template + user_data builder + launch helper. |
| 5h | `aef4018` | `Routes__OpenSearch__Stack` — 5 FastAPI routes mirroring `Routes__Ec2__Playwright`. |
| 5i | `6abf20b` | `sp os` / `sp opensearch` typer commands + `Renderers.py` (Rich tables + panels). Mounted on the main `sp` app. |

**Deferred:** 5g — dashboard generator with a shared `Base__Dashboard__Generator` extracted from `elastic` (touches both sections; best done fresh).

## Phase B step 6 — `sp prom` (1 commit, in-progress)

| Step | Commit | What |
|---|---|---|
| 6a | `1a19d3f` | Foundation — folder + `Safe_Str__Prom__Stack__Name` + `Enum__Prom__Stack__State` + `Prometheus__AWS__Client` skeleton with `PROM_NAMING`. |

**Remaining:** 6b (schemas) → 6c (AWS helpers) → 6d (HTTP probe) → 6e (Service) → 6f (user-data + compose + create_stack) → 6g (routes) → 6h (typer).

## Backfill commits

| Commit | What |
|---|---|
| `98d3991` | Backfilled 7 missing Phase B sub-slice debriefs (5f.1, 5f.2, 5f.3, 5f.4a, 5f.4b, 5h, 5i). |

## Test trajectory

| | |
|---|---|
| Tests at session start | 1061 (pre-existing repo) |
| Tests after Phase A | 1176 (+115 mine) |
| Tests after `sp os` | 1313+ (extra +138 mine) |
| Tests after 6a | 1332+ (extra +19 mine) |
| **My work areas tally** | **251 / 251 green** (`aws/` + `ec2/` + `image/` + `opensearch/` + `prometheus/`) |
| Pre-existing failure | 1 (unchanged): `test_S3__Inventory__Lister::test_empty_region_does_not_pass_region_name` — `lets/cf/inventory` work, network-dependent, predates this branch |

## What's NOT working / NOT shipped

- `sp prom create` — schemas + service + routes + typer all still missing (6b–6h)
- `sp vnc` — entire section not started (B7)
- Phase C — `provision_ec2.py` still has 9-container compose; ports `9090/3000/5001/8080` still in SG; observability containers still bundled
- Phase D — `sp vault-*` / `sp *-ami` / `sp forward-*` commands still flat
- Dashboard auto-import on `sp os create` (5g deferred)
