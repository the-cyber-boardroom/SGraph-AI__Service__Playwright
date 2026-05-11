# Implementation Plan

This doc sequences the work for a Claude Code (Sonnet) session implementing sgi v0.1.0. It is intentionally **execution-oriented**: each milestone has acceptance criteria, gated by tests, with a clear "this is done when…" signal.

The plan is structured around the **simplest-spec-first** principle: build the entire workflow against `ssh_file_server` (the trivial spec) before touching any complex spec. Each later spec is a relatively small increment over the previous one.

---

## Milestones

### M0 — Repo bootstrap (~1 day)

**Goal:** A repo at the target URL with the skeleton, packaging, and CI in place.

| # | Task | Done when |
|---|---|---|
| 0.1 | Create the repo at `https://github.com/SG-Compute/SG-Compute__Image-Builder` | `git clone` works |
| 0.2 | Initial directory structure per [02__architecture/architecture.md](../02__architecture/architecture.md) | All folders exist with `__init__.py` |
| 0.3 | `pyproject.toml` with dependencies (osbot-utils, osbot-aws, typer, rich, zstandard) | `pip install -e .` works |
| 0.4 | `LICENSE`, `README.md`, `version` file | All present, version = `v0.0.1` |
| 0.5 | `humans/dinis_cruz/briefs/` and `team/roles/` skeleton (per [11__librarian/librarian-brief.md](../11__librarian/librarian-brief.md)) | Folders exist with role README placeholders |
| 0.6 | CI pipeline (per [10__dev-ops/dev-ops-brief.md](../10__dev-ops/dev-ops-brief.md)) | First push to dev branch passes a smoke test |
| 0.7 | `sgi --version` works against an empty CLI | `sgi --version` prints v0.0.1 |

**Acceptance:** Anyone can clone the repo, `pip install -e .`, and run `sgi --version`.

---

### M1 — Provider foundations (~2 days)

**Goal:** Storage and Exec_Provider abstractions with their three implementations each, fully tested.

| # | Task | Done when |
|---|---|---|
| 1.1 | `Schema__Storage__Object__Info`, `Schema__Storage__Uri` | Type_Safe classes with tests |
| 1.2 | `Storage` abstract interface | Class defined, all methods raise `NotImplementedError` |
| 1.3 | `Storage__In_Memory` | Full implementation, 100% test coverage |
| 1.4 | `Storage__Local_Disk` | Full implementation, tests against tempdir |
| 1.5 | `Storage__S3` | Full implementation using osbot-aws; tests gated by `SGI_S3_TESTS_ENABLED` |
| 1.6 | `Storage__Factory` | URI scheme dispatch, tests |
| 1.7 | `sgi storage migrate <a> <b>` works for all 9 src/dst combinations | Integration test passes |
| 1.8 | `Schema__Exec__Request`, `Schema__Exec__Result`, `Schema__Exec__File__Transfer` | Type_Safe classes with tests |
| 1.9 | `Exec_Provider` abstract interface | Class defined |
| 1.10 | `Exec_Provider__Twin` with command_log + canned_responses | Full implementation, tests |
| 1.11 | `Exec_Provider__SSH` wrapping osbot-utils SSH | Tests against `localhost` ssh server in CI |
| 1.12 | `Exec_Provider__Sg_Compute` (best-effort text parsing of `sg lc exec`) | Mocked subprocess tests |
| 1.13 | `Exec_Provider__Factory` | Workspace-state-driven dispatch |
| 1.14 | `providers/aws/` helpers (ephemeral launch, key pair, SG ingress) | Implementations + unit tests with mocked osbot-aws |

**Acceptance:** All 9 storage migration combinations work in CI. The Exec Twin and Sg_Compute providers run end-to-end against canned data. The SSH provider runs against a localhost SSH server in CI (using GitHub Actions' built-in SSH agent).

---

### M2 — Workspace and CLI bootstrap (~1 day)

**Goal:** `sgi init`, `sgi version`, `sgi doctor`, basic workspace state management.

| # | Task | Done when |
|---|---|---|
| 2.1 | `Schema__Workspace__State` + `Schema__Workspace__Tracked__Instance` | Type_Safe classes |
| 2.2 | `Workspace__Init` — creates `state.json` and subdirs | `sgi init` works in a fresh directory |
| 2.3 | `Workspace__State__Manager` — read/write `state.json` | Round-trip tests pass |
| 2.4 | `Workspace__Resolver` — find workspace root from cwd, resolve current instance | All target-resolution rules from [03__cli/cli-surface.md](../03__cli/cli-surface.md) implemented |
| 2.5 | Top-level typer app + `Cli__Init.py` | `sgi init`, `sgi version`, `sgi doctor` work |
| 2.6 | `--format`, `--storage`, `--exec-provider`, `--region`, `--quiet`, `--verbose`, `--workspace` global flags | Tests verify each flag |
| 2.7 | `Renderer__Table` and `Renderer__JSON` | Both render the same `Schema__*__Result` consistently |

**Acceptance:** `sgi init` creates a valid workspace, `sgi version` reads the version, `sgi doctor` runs through a checklist and reports.

---

### M3 — Capture and package (~3 days)

**Goal:** `sgi bundle capture` and `sgi bundle capture-from` work; `sgi bundle package` produces a valid bundle.

| # | Task | Done when |
|---|---|---|
| 3.1 | `Schema__Capture__Diff` and `Schema__Capture__Meta` | Schemas with file entries, mtimes, sha256 |
| 3.2 | `Capture__Filesystem` (local-only, via `--source <path>`) | Captures a tempdir change, produces a valid diff |
| 3.3 | `Capture__Filesystem` (remote, via Exec_Provider) | Captures changes on a twin target |
| 3.4 | `Cli__Bundle.capture` and `Cli__Bundle.capture_from` | Both CLI verbs work |
| 3.5 | `Schema__Bundle__Manifest` and `Schema__Bundle__File__Entry` | Schemas with all fields from [05__bundles/bundles-and-storage-layout.md](../05__bundles/bundles-and-storage-layout.md) |
| 3.6 | `Bundle__Packer` — captures → tar.zst + manifest | Round-trip: pack and unpack matches original |
| 3.7 | `Bundle__Sidecar__Builder` — generates stub SKILL.md/USAGE.md/SECURITY.md if not provided | Stub files appear in sidecar.zip |
| 3.8 | `Cli__Bundle.package` | `sgi bundle package <capture> --mode none` produces a valid bundle in workspace |

**Acceptance:** A user can `sgi bundle capture /tmp/some-install/`, then `sgi bundle package <capture> --mode none`, and get a valid bundle in `workspace/bundles/`.

---

### M4 — Publish, list, resolve, load (~3 days)

**Goal:** Bundles round-trip through Storage: publish → list → resolve → load.

| # | Task | Done when |
|---|---|---|
| 4.1 | `Ifd__Path__Builder` | Path builder tests pass; reserved chars handled |
| 4.2 | `Bundle__Publisher` — uploads manifest, payload, sidecar, publish.json to Storage | Storage tree matches the spec |
| 4.3 | `Bundle__Publisher` — updates `catalog.json` atomically | Catalog reflects published bundles |
| 4.4 | `Bundle__Resolver` — short URI → concrete IFD path → bytes | All forms of URI resolve correctly |
| 4.5 | `Bundle__Verifier` — sha256 check on payload and per-file | Tests with corrupted bundles fail verification |
| 4.6 | `Cli__Bundle.publish`, `list`, `info`, `resolve`, `verify`, `diff`, `deregister` | All CLI verbs work |
| 4.7 | `Load__Downloader` — pulls bundle from Storage to local | Tested with all three storage backends |
| 4.8 | `Load__Extractor` — extracts payload on target via Exec_Provider | Files appear at correct paths |
| 4.9 | `Load__Transparent` — applies perms/owner/xattrs from manifest | P2: end-to-end byte-equal verification |
| 4.10 | `Cli__Bundle.load <bundle-uri> <target>` | A bundle captured locally can be loaded onto a twin target |

**Acceptance:** Full round-trip: capture a tempdir → package → publish to Storage__Local_Disk → load onto a twin target → verify files identical.

---

### M5 — First spec end-to-end (~2 days)

**Goal:** `ssh_file_server` works on real AWS. **The cold-start milestone.**

| # | Task | Done when |
|---|---|---|
| 5.1 | `sg_image_builder_specs/ssh_file_server/` package skeleton | Tests pass |
| 5.2 | Spec manifest in `manifest.py` | `sgi spec info ssh_file_server` returns correct data |
| 5.3 | `default.json` recipe (empty steps, just AL2023) | Recipe validates |
| 5.4 | `tests/end_to_end/test_ssh_file_server.py` | Tests defined |
| 5.5 | `Cli__Spec.list/info/test-suite/scaffold` | All spec verbs work |
| 5.6 | `Cli__Test.list/run` | `sgi test run ssh_file_server --launch` works |
| 5.7 | `Cli__Instance.launch` for SSH provider — ephemeral EC2 lifecycle | EC2 instance created with key pair + SG, torn down on completion |
| 5.8 | E2E test: `sgi test run ssh_file_server --launch` produces a passing test run on real AWS | All 3 tests pass against a freshly-launched g5 |

**Acceptance:** `sgi test run ssh_file_server --launch` passes against a real EC2 instance. Cold-start measurement captured in `workspace/benchmarks/`.

---

### M6 — Benchmark (~1 day)

**Goal:** Three canonical moments measured and reported.

| # | Task | Done when |
|---|---|---|
| 6.1 | `Timing__Tracker` context manager | Records named sub-steps with millisecond precision |
| 6.2 | `Schema__Benchmark__Run` + `Schema__Benchmark__Measurements` | Type_Safe classes |
| 6.3 | `Benchmark__First_Load` | Times bundle download + extract |
| 6.4 | `Benchmark__Boot` | Times boot-to-service-ready |
| 6.5 | `Benchmark__Execution` | Times workload op |
| 6.6 | `Benchmark__Cold_Start` (composite) | Times the full chain |
| 6.7 | `Benchmark__Reporter` — aggregates `workspace/benchmarks/*.json` | Tables print with p50/p95/max |
| 6.8 | `Cli__Benchmark.*` | All benchmark verbs work |

**Acceptance:** Ten cold-start runs of `ssh_file_server` produce a benchmark report with sub-step breakdown.

---

### M7 — Strip (basic) (~2 days)

**Goal:** `strip --mode debug` works end-to-end with a static keep-list. Modes `service` and `minimal` are sketched but not gating M7 completion.

| # | Task | Done when |
|---|---|---|
| 7.1 | `Schema__Strip__Mode`, `Schema__Strip__Plan`, `Schema__Strip__Candidate` | Schemas defined |
| 7.2 | `Strip__Mode__None`, `Strip__Mode__Debug` (static keep-list) | Both modes implemented |
| 7.3 | `Strip__Analyser` for debug mode (static list, no test run) | Produces analysis |
| 7.4 | `Strip__Plan__Builder` | Produces immutable plans |
| 7.5 | `Strip__Executor` — applies plans on target | Removes files; records sha256s for restore |
| 7.6 | `Strip__Verifier` — re-runs spec test suite | Pass/fail report |
| 7.7 | `Cli__Strip.*` | All strip verbs work |
| 7.8 | `sgi strip bake <bundle-uri> --mode debug --publish` | Produces a smaller bundle at a bumped IFD path |

**Acceptance:** A python_server bundle, stripped --mode debug, is ~30% smaller and passes the spec test suite. The stripped version published at v0.1.1.

---

### M8 — Recipe orchestration (~1 day)

**Goal:** Multi-step recipes execute correctly.

| # | Task | Done when |
|---|---|---|
| 8.1 | `Schema__Recipe`, `Schema__Recipe__Step`, `Schema__Recipe__KPIs` | Schemas defined |
| 8.2 | `Recipe__Builder` and `Recipe__Validator` | Recipes validate (refs resolve, schemas correct) |
| 8.3 | `Recipe__Publisher` — IFD-versioned to Storage | Published recipes in catalog |
| 8.4 | `Recipe__Executor` — runs steps in order on target | All steps execute; per-step test_after honoured |
| 8.5 | `Cli__Recipe.*` | All recipe verbs work |

**Acceptance:** `python_server`'s default recipe (2 steps) executes end-to-end on a fresh target.

---

### M9 — Remaining CPU specs (~5 days)

In order: `python_server` → `node_server` → `graphviz` → `docker` → `ollama_disk` → `ollama_docker`.

For each spec:

1. Create the spec package
2. Define manifest + recipe
3. Write the test suite
4. Capture a bundle from a build instance
5. Package, publish
6. `sgi test run <spec> --launch` passes
7. Run `sgi benchmark cold-start <spec>` 5×; record KPIs

The `ollama_disk` spec is the big one: it introduces the model-as-separate-bundle pattern. The `ollama_docker` spec proves docker images can be bundles.

**Acceptance:** All 6 CPU specs pass their E2E tests on real AWS, with measurable KPIs in `benchmarks/`.

---

### M10 — GPU specs (~3 days)

`vllm_disk` then `vllm_docker`.

For each:

1. Start from DLAMI AL2023 OSS variant
2. Capture vLLM + model
3. Get the vLLM launch flags right (the working set from `Section__VLLM.py` in sg-compute)
4. Test suite verifies inference works
5. Benchmark cold-start

**Acceptance:** `sgi test run vllm_docker --launch` produces a working vLLM serving Qwen, with `/v1/models` returning 200, all in under 90 seconds.

---

### M11 — Visualisation and events (~1 day)

| # | Task | Done when |
|---|---|---|
| 11.1 | `Events__Emitter` and `Schema__Event` | Every operation emits events |
| 11.2 | `Events__Sink__JSONL` (default) | Events appear in `workspace/events/*.jsonl` |
| 11.3 | `Events__Sink__Elasticsearch` (optional) | Events ship to a configured ES instance |
| 11.4 | `Cli__Events.*` | tail/query/export work |
| 11.5 | One Kibana dashboard JSON for cold-start trends | Importable into Kibana, renders data |

**Acceptance:** Running `sgi test run vllm_docker --launch` produces events visible in `workspace/events/`, and (optionally) ship to ES.

---

### M12 — Distribution and polish (~1 day)

| # | Task | Done when |
|---|---|---|
| 12.1 | `python -m zipapp` build target | `sgi.zipapp` runs as `python sgi.zipapp <command>` |
| 12.2 | Tagged v0.1.0 release | GitHub release with `sgi.zipapp` attached |
| 12.3 | All E2E tests green in CI | Tagged-release pipeline passes |
| 12.4 | Documentation pass | `README.md`, `docs/` filled out |

**Acceptance:** A user can download `sgi.zipapp` from the GitHub release page and run it on any Linux host with Python 3.11.

---

## Sequencing notes

- **M0 must complete before M1.** Setup precedes everything.
- **M1 and M2 can run in parallel** if there are two developers — providers and workspace are independent.
- **M3 depends on M1 and M2.** Capture needs Exec_Provider and Workspace.
- **M4 depends on M3.** Publish/load need bundles.
- **M5 is the first integration milestone** and must complete before any spec work. It's the "does this thing actually work?" gate.
- **M6, M7, M8 can run in parallel** after M5. They're all independent of each other.
- **M9 spec by spec, in the order listed.** Each spec compounds learning.
- **M10 only after M9.** GPU adds cost and complexity; we want CPU mileage first.
- **M11 throughout.** Events should be emitted from M3 onwards; the visualisation work is the last step.
- **M12 is the release.** Don't release before M10 is green.

## Total estimate

| Milestone | Days |
|---|---|
| M0 — Bootstrap | 1 |
| M1 — Providers | 2 |
| M2 — Workspace + CLI | 1 |
| M3 — Capture + package | 3 |
| M4 — Publish + load | 3 |
| M5 — First spec E2E | 2 |
| M6 — Benchmark | 1 |
| M7 — Strip basic | 2 |
| M8 — Recipes | 1 |
| M9 — CPU specs | 5 |
| M10 — GPU specs | 3 |
| M11 — Visualisation | 1 |
| M12 — Distribution | 1 |
| **Total** | **~26 days** for v0.1.0 |

For one developer working full-time: ~5 weeks. With parallelism (two developers post-M2): ~3.5 weeks.

## Acceptance for v0.1.0 release

The release is ready when ALL of these are true:

- [ ] `sgi.zipapp` is published as a GitHub release artefact
- [ ] All 9 specs pass their E2E tests on real AWS
- [ ] `sgi test run vllm_docker --launch` reaches `/v1/models == 200` in under 90s p50
- [ ] All 21 principles from [01__principles/principles.md](../01__principles/principles.md) are honoured (code review)
- [ ] All four storage backends pass migration round-trip in CI
- [ ] `sgi storage migrate s3 file` produces a complete air-gap-portable registry
- [ ] CI pipeline gates merge on unit + integration tests; runs E2E on tags
- [ ] `humans/`, `team/`, `docs/` folders complete per the Librarian brief
- [ ] No direct boto3 imports outside `osbot-aws` and `providers/aws/`
- [ ] No direct `paramiko`/`subprocess` outside `providers/exec/`
- [ ] Sidecar stubs generated for every bundle; at least 3 specs have real (non-stub) SKILL.md/USAGE.md
