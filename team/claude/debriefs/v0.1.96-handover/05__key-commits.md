# 05 — Key Commits to Read

When you want to understand a pattern or seam, read the commit that introduced it. These are the high-signal landmarks; the per-slice debriefs in `team/claude/debriefs/2026-04-26__playwright-stack-split__*.md` carry the full commentary.

## Phase A foundations

| Commit | Read for |
|---|---|
| `4ee540c` | **`Stack__Naming` shared class.** The base pattern every sister section reuses. Prefix-never-doubled + sg-suffix-on-GroupName logic. Used by `ELASTIC_NAMING`, `OS_NAMING`, `PROM_NAMING`. |
| `0162e93` | **`Image__Build__Service` shared docker-build pipeline.** Type_Safe Schema-Request → Schema-Result. `_Fake_Docker_Client` test pattern (real subclass, no mocks). Stage-context happy path + tempdir-cleanup-on-failure. |
| `68a6c85` | **`Ec2__AWS__Client` skeleton.** Establishes the AWS-boundary class-with-method-seam pattern (`ec2()` is the override point). Module-level pure helpers + class with `find_instances` etc. |
| `cde60c5` | **Typer wrappers — `cmd_list`/`cmd_info`/`cmd_delete` reduced.** Demonstrates the Tier-2A → Tier-1 reduction: thin wrapper calls service, renders schema. The pattern `sp os` typer commands followed. |

## Phase B `sp os` landmarks

| Commit | Read for |
|---|---|
| `b0f3805` | **Foundation slice + the `os` → `opensearch` rename.** Folder layout precedent. Surfaced the stdlib-shadowing gotcha. |
| `9a1e04e` | **6 schemas + collection.** Type_Safe data classes for the section. Defensive `Info-never-includes-password` test pattern. |
| `f5dcde7` | **4 small AWS helpers split per concern.** This is THE template for sister-section AWS surfaces. SG / AMI / Instance / Tags each in their own ~50-line file with their own ~80-line test. |
| `05c0bb7` | **HTTP base + probe pattern.** `verify=False` for self-signed TLS, basic auth, scoped urllib3 warning suppression. Probes return `{}` / `False` on any failure (caller maps to `-1` sentinels). |
| `82afd0e` | **Service read paths.** Shows how to compose `aws_client` + `probe` + `mapper` + `ip_detector` + `name_gen` into a Tier-1 orchestrator. `setup()` lazy-init. |
| `0a09731` | **Launch helper.** Base64 UserData, single-node `MinCount=MaxCount=1`, optional IAM profile. The clean run_instances seam. |
| `2b21126` | **`create_stack` end-to-end.** This is THE proof-of-concept for the whole sister-section model. Default resolution flow (name / ip / password / ami) → composition (sg → tags → compose → user-data → launch). |
| `aef4018` | **FastAPI routes (Tier 2B).** 5 routes, zero logic in handlers — `service.method().json()`. `_Fake_Service(OpenSearch__Service)` test pattern with FastAPI TestClient. |
| `6abf20b` | **Typer commands + Renderers (Tier 2A).** Splits Rich rendering into a separate `Renderers.py`. Wires onto main `sp` app via `add_typer` + hidden short alias. |

## Documentation backfill

| Commit | Read for |
|---|---|
| `98d3991` | Backfill of 7 missing Phase B sub-slice debriefs. Useful as a reference for the per-slice shape. |

## How to bring up speed quickly

A fresh agent should:

1. `git log --oneline cde60c5^..6abf20b` — see the work in commit-message form
2. Read **`f5dcde7`** in full — the 4-helper split is the most replicated pattern
3. Read **`2b21126`** in full — the `create_stack` composition is the proof of the whole model
4. Skim the per-slice debriefs for any commit that's unclear
