# Debrief — 2026-05-10: SG/Compute — Spec CLI Builder bug-fix sweep + AMI feature

**Date:** 2026-05-10
**Status:** COMPLETE (one PR open: `claude/add-spec-documentation-XB9ug`)
**Versions shipped:** `sg_compute v0.2.7` (Phase 3 Ollama wedge — landed before this session) → `v0.2.8` (this session: AMI surface)
**Commits (newest first):**
| Commit    | Headline                                                                  |
|-----------|---------------------------------------------------------------------------|
| `cfd99c1` | fix(shutdown): register auto-terminate timer before spec-specific sections |
| `9f0da84` | feat(v0.2.8): ami list/bake/wait/delete on Spec__CLI__Builder              |
| `f028b8b` | feat(list): add pricing column to render_list                              |
| `2ebc4ac` | docs(plan): v0.2.8 — Docker migration onto Spec__CLI__Builder              |
| `fabd828` | Add ssm-user to docker group in Section__Docker                            |
| `0afd0f5` | feat(ollama): python3.13, spot-by-default, fix --wait health probe        |
| `c0e9387` | fix(ollama): SSM access, disk-size wiring, --wait name, delete confirm    |
| `2005614` | fix(sp): wire sp ollama to Cli__Ollama module directly                     |

**Branch:** `claude/add-spec-documentation-XB9ug` — pushed but **not merged to `dev`** at the time of writing.

---

## TL;DR for the next agent

1. **Two big things shipped:** the v0.2.7 Ollama wedge (Builder-driven CLI) is alive on real AWS; v0.2.8 added a generic `ami list/bake/wait/delete` sub-typer to every spec built via `Spec__CLI__Builder` (currently only Ollama uses the Builder; Docker is next per `team/comms/plans/v0.2.8__docker-on-builder.md`).

2. **Eight Ollama-wedge bugs surfaced and were fixed** AFTER the v0.2.7 merge — every one was masked by unit tests that never invoked real AWS. **The single most important takeaway: live-AWS smoke is mandatory for any future spec migration onto the Builder.** The Docker plan (`v0.2.8__docker-on-builder.md`) has the full list and explicitly enforces this.

3. **One open question for the user**: typer help panels show no per-command description because we comply with CLAUDE.md rule 8 (no docstrings). User has not yet decided whether to relax that for typer help text. See [§ Open questions](#open-questions).

4. **Reality doc and decisions log NOT updated this session.** The librarian/historian work is a follow-up. See [§ Follow-ups](#follow-ups).

---

## What was done

### Part A — Ollama wedge bug-fix sweep (commits `2005614` → `fabd828`)

The Phase-3 Ollama wedge had landed (`159c4f4`) before this session. Live testing surfaced **eight** bugs that unit tests had not caught. All fixed:

| #  | Bug                                                                           | Fix                                                                                                                                                                           | Commit    |
|---:|-------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| L1 | `req.stack_name.__init__(name)` is a no-op (Safe_Str inherits immutable str)  | `setattr(req, 'stack_name', name)` in Builder; extract real name from `resp.stack_info` for `--wait`                                                                          | `c0e9387` |
| L2 | Health probe used `https://` against Ollama's plain-HTTP API on :11434         | Added `health_scheme` to `Schema__Spec__CLI__Spec`; Ollama sets `'http'`                                                                                                       | `0afd0f5` |
| L3 | Health probe returned early when no public IP yet → `--wait` failed instantly | Restructured `Spec__Service__Base.health()` to poll the entire flow (stack-info + URL probe) inside one deadline loop                                                          | `0afd0f5` |
| L4 | Stack launched without IAM instance profile → SSM agent could not register    | `PROFILE_NAME='playwright-ec2'` on `Ollama__Service.create_stack`; `EC2__Launch__Helper.run_instance` accepts `instance_profile_name`                                          | `c0e9387` |
| L5 | `--disk-size` silently dropped (`EC2__Launch__Helper` ignored the arg)        | Added `disk_size_gb` + `BlockDeviceMappings` (gp3) to `run_instance`; default raised to 250 GiB; persisted as `StackDiskGB` tag and rendered in `info`                          | `c0e9387` |
| L6 | Bool-default-true typer flags need `--flag/--no-flag` (otherwise no opt-out)  | Builder auto-emits `--flag/--no-flag` syntax when the extra-create option default is `True`                                                                                   | `c0e9387` |
| L7 | `ssm-user` missing from docker group → every SSM session needed sudo for docker | `usermod -aG docker ssm-user || true` added to `Section__Docker.py`                                                                                                          | `fabd828` |
| L8 | `provision_ec2.py` imported `app` from empty `__init__.py` (CLAUDE.md rule 22) | Direct module import: `from sg_compute_specs.ollama.cli.Cli__Ollama import app as _ollama_app`                                                                                | `2005614` |

Plus user-experience polish:
- `--with-claude` ran a non-existent `ollama run claude --model X` command — fixed to `ollama run {model_name}`
- `delete` confirm now defaults to Y on Enter (D7 contract)
- Spot instances by default (`--use-spot/--no-use-spot`, ~70% cheaper g5.xlarge)
- Python 3.13 in the boot venv (DLAMI's system python is 3.9; AL2023 repo carries 3.13 natively via `dnf install python3.13`)

### Part B — `pricing` column in `render_list` (commit `f028b8b`)

`Schema__Ollama__Info.spot` already populated by the mapper post-`0afd0f5`. The base `render_list` in `Spec__CLI__Renderers__Base.py` got a `pricing` column showing `[cyan]spot[/]` or `[dim]on-demand[/]` whenever the info object has a `spot` attribute (hasattr-guarded so non-spot-aware specs render an empty cell rather than crashing).

### Part C — AMI surface on the Builder (commit `9f0da84`, **v0.2.8**)

Added a generic `ami` sub-typer to every spec built via `Spec__CLI__Builder`. Currently benefits Ollama; Docker will inherit on migration.

```
sp <spec> ami list                                  — list spec-tagged AMIs
sp <spec> ami bake [name] [--name N] [--reboot] [--wait]
                                                    — CreateImage from a running stack
sp <spec> ami wait <ami-id>                         — block until state=available
sp <spec> ami delete <ami-id> [--yes]               — deregister + delete snapshots
```

Key implementation details:
- `AMI__Service` (new, `sg_compute/core/ami/service/AMI__Service.py`) **extends** `AMI__Lister` so the existing `/api/amis` REST route automatically benefits from richer info too
- `Schema__AMI__Info` gained `source_stack` + `source_instance` (read from EC2 tags by `AMI__Lister._map_image`)
- Tag scheme: `sg-compute-spec` (filter), `sg-source-stack`, `sg-source-instance`, `Name`
- `--reboot` defaults OFF (no downtime for live stack); `--wait` polls `describe_images` on a 30-min ceiling (covers the 8–15 min bake of a 250 GiB Ollama AMI)
- `Spec__CLI__Builder._wait_ami_available` is the polling helper; mirrors the `_wait_healthy` pattern from v0.2.7
- 3 new CLI tests in `test_Cli__Ollama.py` (subcommand structure, bake flags, delete arg) — 11 tests total, all green

### Part D — Auto-terminate timer placement bug (commit `cfd99c1`)

User reported a 1-hour spot instance running for 3 hours.

**Root cause:** `Section__Shutdown` was the **last** item in `Ollama__User_Data__Builder.parts`. With `set -euo pipefail` at the top of the user-data script, any earlier failure (e.g. `ollama pull` network blip) exited the script before `systemd-run --on-active=1h /sbin/shutdown -h now` could register the timer. Result: the instance kept running indefinitely.

**Fix:** Compute the shutdown fragment first and inject it at **position 2** (right after `Section__Base`, before any spec work that could fail). Verified in the rendered output: timer at line 15, Ollama install at line 22.

Also fixed a misleading comment in `EC2__Launch__Helper.py` — the old comment claimed "spot always terminates on shutdown" which is only true for AWS-initiated spot interruptions, not OS-initiated shutdown. For non-hibernation spot instances OS shutdown does still terminate, but the comment now accurately explains the skip rather than misleading.

### Part E — Plan document (commit `2ebc4ac`)

Wrote `team/comms/plans/v0.2.8__docker-on-builder.md` — a Sonnet-executable plan for migrating Docker onto the Builder (Phase 4 / spec #1). Key feature: bakes in **all 8 Ollama-wedge lessons** as non-negotiable checks during the Docker migration, and makes live-AWS smoke mandatory for the Docker PR.

---

## Failure classification

### Good failure — `bad-tests-mask-real-bugs`

Eight bugs in v0.2.7 were caught only on real AWS: `__init__` no-op, IAM profile, disk wiring, health scheme, public-IP polling, dual-flag bool, ssm-user docker group, empty `__init__.py` imports. The **78 unit tests** that shipped with `159c4f4` ran the typer help surface and the Type_Safe schemas but never invoked AWS. We now know the entire class of failure-mode and the v0.2.8 plan enforces live smoke.

This is a **good failure** because:
- It surfaced fast (within hours of merge)
- It informed the v0.2.8 plan (lessons table is the centerpiece)
- It changed our acceptance bar going forward (live smoke is mandatory)

### Bad failure — `shutdown-timer-position`

The Ollama wedge merged with `Section__Shutdown` placed at the end of the parts list. This was a latent bug that would have been caught by:
- A unit test asserting "rendered user-data has the shutdown timer registered before any `set -euo pipefail`-failable command"
- Any code review focused on "what happens if the user-data script fails partway"

Neither happened. The bug only surfaced when a real stack ran for 3× its max-hours budget — costing the user actual dollars.

This is a **bad failure** because:
- It was visible to anyone who read the user-data builder + thought about `set -euo pipefail` interaction
- It was not caught by tests (no test for ordering invariants)
- It cost real money before being detected

**Follow-up:** add a property test asserting Section__Shutdown.render() output appears in the user-data **before** the first invocation of any subprocess that could fail (curl, ollama pull, dnf install of an external repo, etc.). Open to all spec user-data builders.

---

## Lessons learned

### Type_Safe / Safe_Str gotchas

- **`Safe_Str.__init__()` is a no-op** because `Safe_Str` inherits `str`, which is immutable. `obj.field.__init__(value)` does NOT update the field. Use `setattr(obj, 'field', value)` exclusively.
- This pattern (`req.stack_name.__init__(name)`) is **still present** in `sg_compute_specs/docker/cli/Cli__Docker.py:83-84` (legacy CLI) and possibly other legacy CLIs. The Docker migration plan notes this as L1 for cleanup.

### Typer / Builder gotchas

- **Bool option with default `True` requires `--flag/--no-flag`** syntax in typer or there is no way to opt out. Builder now emits this automatically for any `extra_create_options` entry where `t is bool and d is True`.
- **Typer help panels are blank without docstrings.** CLAUDE.md rule 8 forbids docstrings. Open question for user (see below).
- **Dynamic typer signatures via `inspect.Signature`** are needed because Type_Safe's metaclass conflicts with typer's reflection-based introspection. Builder is intentionally NOT a Type_Safe class. (R1 from the v0.2.6 plan.)

### EC2 / boot lifecycle gotchas

- **`set -euo pipefail` + ordered fragments = brittle.** Any setup that registers a side-effect (timer, watchdog, log shipper) MUST run before spec-specific work that can fail. Position 2 is "after base, before everything else."
- **`InstanceInitiatedShutdownBehavior` for spot:** for non-hibernation spot, OS shutdown terminates regardless. The flag is silently ignored — safe to skip but the comment must say *why* (the v0.2.7-era comment was misleading).
- **SSM requires IAM instance profile.** Without `playwright-ec2` profile, SSM agent never registers, `aws ssm start-session` fails. Every Builder-using spec must pass `instance_profile_name='playwright-ec2'` to `EC2__Launch__Helper.run_instance`.
- **`ssm-user` is the SSM session user.** It is NOT the same as `ec2-user`. For commands inside SSM sessions to work without sudo (docker etc.), `ssm-user` must be in the relevant groups. Currently only Docker stacks add this; verify per-spec needs as new specs migrate.

### AMI / tagging gotchas

- **`AMI__Lister` filters on tag `sg-compute-spec`**. Any AMI baked outside this convention (e.g. baked manually via console) will not appear in `sp <spec> ami list`. The `bake` verb sets all four tags correctly: `sg-compute-spec`, `sg-source-stack`, `sg-source-instance`, `Name`.
- **`deregister_image` does NOT delete snapshots.** Snapshots survive and continue billing. `AMI__Service.delete()` must explicitly call `delete_snapshot` for each snapshot referenced in `BlockDeviceMappings`. Returns `(deregistered: bool, snapshots_deleted: int)` so the renderer can report both.

### CLAUDE.md alignment

- **Rule 22 (empty `__init__.py`)** bit us through `provision_ec2.py` importing `app` from an empty file. Always import directly from the module containing the symbol.
- **Rule 8 (no docstrings)** is in tension with typer help quality. See open question.
- **Rule 13 (no double-prefixing AWS Name tag)** — Ollama mapper uses `tag_value(details, TAG_STACK_NAME)` directly so no double-prefix risk.

---

## Files changed this session

### New files
- `sg_compute/core/ami/service/AMI__Service.py` — bake/delete/describe-state, extends `AMI__Lister`
- `team/comms/plans/v0.2.8__docker-on-builder.md` — Sonnet-executable plan for the Docker migration

### Modified files (sg_compute core)
- `sg_compute/cli/base/Schema__Spec__CLI__Spec.py` — added `health_scheme: str = 'https'`
- `sg_compute/cli/base/Spec__CLI__Builder.py` — `setattr` fix, `_register_ami`, `_wait_ami_available`, dual-flag bool emit, delete confirm default
- `sg_compute/cli/base/Spec__CLI__Renderers__Base.py` — `render_ami_list/_bake/_delete/_wait`; `pricing` column on `render_list`; expanded info key list
- `sg_compute/core/ami/schemas/Schema__AMI__Info.py` — added `source_stack`, `source_instance`
- `sg_compute/core/ami/service/AMI__Lister.py` — read `sg-source-stack` / `sg-source-instance` tags; shared TAG constants
- `sg_compute/core/spec/Spec__Service__Base.py` — restructured `health()` to poll within deadline
- `sg_compute/platforms/ec2/helpers/EC2__Launch__Helper.py` — `disk_size_gb` (BlockDeviceMappings), `instance_profile_name`, `use_spot` (InstanceMarketOptions), corrected comment
- `sg_compute/platforms/ec2/user_data/Section__Agent_Tools.py` — python3.13
- `sg_compute/platforms/ec2/user_data/Section__Claude_Launch.py` — fixed bogus `ollama run claude --model X`
- `sg_compute/platforms/ec2/user_data/Section__Docker.py` — `usermod -aG docker ssm-user`
- `sg_compute/version` — `v0.2.7` → `v0.2.8`

### Modified files (sg_compute_specs/ollama)
- `cli/Cli__Ollama.py` — `health_scheme='http'`, `use_spot=True` extra
- `schemas/Schema__Ollama__Create__Request.py` — `disk_size_gb` default 250 GiB; `use_spot: bool = True`
- `schemas/Schema__Ollama__Info.py` — `disk_size_gb`, `spot`
- `service/Ollama__Service.py` — `PROFILE_NAME='playwright-ec2'`; `disk_gb` and tags wiring; `cli_spec()` returns `health_scheme='http'`
- `service/Ollama__Stack__Mapper.py` — `TAG_DISK_GB = 'StackDiskGB'`; populates `disk_size_gb` and `spot`
- `service/Ollama__User_Data__Builder.py` — Section__Shutdown moved to position 2

### Modified files (scripts / tests)
- `scripts/provision_ec2.py` — direct `Cli__Ollama` import
- `sg_compute_specs/ollama/tests/test_Cli__Ollama.py` — 3 new AMI subcommand tests
- `sg_compute_specs/ollama/tests/test_Schema__Ollama__Create__Request.py` — `disk_size_gb == 250`
- `sg_compute__tests/helpers/user_data/test_Section__Agent_Tools.py` — python3.13 assertion
- `sg_compute__tests/helpers/user_data/test_Section__Docker.py` — ssm-user assertion

---

## Test status

All in-scope tests pass:
- `pytest sg_compute_specs/ollama/tests/` — **28 passed**
- `pytest sg_compute__tests/helpers/user_data/` — **32 passed**
- `pytest sg_compute_specs/ollama/tests/ sg_compute__tests/helpers/ sg_compute__tests/cli/ sg_compute__tests/core/` — 180 pass; **2 pre-existing Firefox failures on `dev` (unrelated)**: `test_set_credentials_raises_not_implemented`, `test_upload_mitm_script_raises_not_implemented`. Confirmed these fail on `dev` before this session's branch existed.

Pre-existing environment gap (also unrelated): `sg_compute__tests/control_plane/` and `sg_compute__tests/vault/` fail at collection time with `ModuleNotFoundError: No module named 'fastapi'`. The local dev environment is missing `fastapi`. Tests run fine in CI.

---

## Open questions

1. **Typer help text vs CLAUDE.md rule 8 (no docstrings).** All Builder-generated commands currently show empty help panels because adding a docstring would violate rule 8. Options:
   - (a) Accept blank help (current state) — keeps rule 8 strict
   - (b) Allow ONE-line docstrings on typer command functions only — relaxes rule 8 for typer-only
   - (c) Pass `help=...` through typer.Argument/typer.Option metadata — verbose but compliant

   Recommend (b) with a note in CLAUDE.md scoping the exception. **Pending user decision.**

2. **Section__Shutdown ordering across other specs.** Docker uses a single-template user-data builder with `shutdown_line` at the end of `FOOTER_TEMPLATE`. Same brittleness pattern. **Should be fixed during the Docker migration to the Builder, not before** (otherwise we'd be doing it twice). Tracked as an L9 to add to the v0.2.8 Docker plan.

---

## Follow-ups (sized for next session)

### Must-do before merging this branch

- [ ] **Live AWS smoke for v0.2.8 AMI surface.** User intends to bake their claude+vllm AMI. Confirm: `sp ollama ami bake … --wait` works end-to-end; `sp ollama ami list` shows the new AMI with state=available; `sp ollama create --ami <id>` succeeds. The user is on us-east-1.
- [ ] **Reality doc update.** `team/roles/librarian/reality/sg-compute/index.md` needs a v0.2.8 entry recording the AMI surface, the `pricing` column, the shutdown-ordering fix, and the L1–L8 lessons table.
- [ ] **Decisions log.** Add the corrected `InstanceInitiatedShutdownBehavior` reasoning, the AMI tag scheme, and the Section__Shutdown ordering invariant to `library/reference/v{version}__decisions-log.md`.

### Phase 4 — Docker on Builder (next big slice)

The plan is fully written: **`team/comms/plans/v0.2.8__docker-on-builder.md`**. It is Sonnet-executable. Recommended sequence:

1. Read the plan top-to-bottom. **Do not skip the L1–L8 lessons table.**
2. Confirm the legacy `req.__init__` bug is gone in the new shape (L1).
3. Confirm `health_scheme` / `health_port` / `health_path` matches the actual Docker sidecar before writing the `_cli_spec` (L2).
4. Confirm `Schema__Docker__Health__Response` has no external consumers before deletion (option A in the plan); fall back to bridging if it does.
5. Live AWS smoke is **mandatory** for this PR (per § Acceptance gate in the plan).

### Phase 5 — `agent_tools` sidecar HTTP surface (Group F)

Deferred from v0.2.7 explicitly. Adds `run-python / read-file / write-file / http-get / http-post` routes on `Fast_API__Host` so the boot-installed Python venv is reachable over HTTP. Independent of Phase 4 — could be done in parallel by a separate session. **No plan written yet.** Suggested filename: `team/comms/plans/v0.2.9__agent-tools-sidecar.md`.

### Phase 6 — `Cli__Compute__Node` generic delegator

Deferred from the v0.2.6 rollout plan. Replace `_DISPATCHERS['docker']` etc. with a generic delegator that calls `EC2__Platform.create_node(spec_id=..., base_request=...)`. Best done after spec #2 (podman) lands so the generic shape is exercised against two clients. **No plan written yet.**

### Open observability bug

A user-data script that aborts before `Section__Shutdown` registers a timer leaves a costly running spot instance. Even with the position-2 fix, **other failure modes exist** — e.g. a syntax error in `Section__Base` itself. Worth adding an EventBridge / CloudWatch alarm: any instance tagged `sg-compute-spec=<x>` running > max_hours+30min triggers an alert. Out of scope for this session but cheap insurance.

---

## Where to start (if continuing this work)

**Read these in order:**

1. **This debrief** — you are here.
2. `team/comms/plans/v0.2.8__docker-on-builder.md` — the next big slice if continuing Phase 4. Includes lessons L1–L8 baked in as required checks.
3. `sg_compute_specs/ollama/cli/Cli__Ollama.py` — the canonical reference for a Builder-based CLI (~90 LOC).
4. `sg_compute_specs/ollama/service/Ollama__Service.py` — reference for `Spec__Service__Base` extension; note `cli_spec()` and `create_node()` patterns.
5. `sg_compute/cli/base/Spec__CLI__Builder.py` — read `_register_ami` and `_wait_ami_available` for the AMI sub-typer pattern; read `_register_create` for how `extra_create_options` get spliced into a dynamic typer signature.
6. `sg_compute/cli/base/Spec__CLI__Renderers__Base.py` — base renderers; the `hasattr(s, 'spot')` guard pattern is the way new optional info fields should be rendered.
7. `sg_compute/core/ami/service/AMI__Service.py` — extends `AMI__Lister`; note tag scheme constants.
8. `team/comms/plans/v0.2.6__spec-cli-base__00__overview.md` and the Phase 1+2+3 plan files — for context on D1–D8 decisions and R1 (typer/Type_Safe metaclass conflict).

**Don't bother reading these unless the specific topic comes up:**
- `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py` — legacy 550-LOC CLI; reference for `ami_app` sub-typer pattern (already absorbed into the Builder)
- The pre-v0.2.6 SP CLI tree — slated for Phase 5 decommission

**Critical files to NOT touch unless deliberately changing the contract:**
- `sg_compute/cli/base/Schema__Spec__CLI__Spec.py` — adding fields here is a contract change; affects every Builder-using spec
- `sg_compute/cli/base/Spec__CLI__Defaults.py` — D2 (`DEFAULT_MAX_HOURS=1`) is a hard contract decision per the v0.2.6 plan
- `sg_compute/core/ami/service/AMI__Lister.py` — consumed by `Routes__Compute__AMIs` REST route; signature changes break the dashboard

---

## What to take into account next session

- **Typer wraps function signatures via `inspect.signature`.** Any change to Builder's command registration must preserve dynamic-signature compatibility (R1). Don't make Builder a Type_Safe class.
- **The branch `claude/add-spec-documentation-XB9ug` is not merged.** The next agent should either continue work on this branch (preferred) or open a PR if the user is ready. Do not start a new branch off `dev` — you'll miss the v0.2.8 changes.
- **Live AWS region for testing**: user is on `us-east-1` for the Ollama+claude+vllm work. Default region in code is `eu-west-2`. Always pass `--region us-east-1` for Ollama smoke tests in this user's environment.
- **Cost**: g5.xlarge spot in us-east-1 is ~$0.30/hr. Always pair smoke tests with `--max-hours 1` and `sp ollama delete` after.
- **`/ultrareview`** is not available to agents — only the user can launch it. If you think the branch needs a multi-agent review before merging, suggest `/ultrareview <branch>` to the user; do NOT attempt to invoke it.
