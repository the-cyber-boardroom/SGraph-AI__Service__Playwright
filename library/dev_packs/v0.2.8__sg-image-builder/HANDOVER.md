# HANDOVER — sgi v0.1.0 Developer Onboarding

**Audience:** Dev agent starting work in [`SG-Compute/SG-Compute__Image-Builder`](https://github.com/SG-Compute/SG-Compute__Image-Builder) (fresh repo, fresh session)
**Pre-conditions (two tiers):**
- **M0 (repo bootstrap, CI, scaffolding — no sgi code yet)** can start **in parallel** with the validation spike that's running in `SGraph-AI__Service__Playwright`. Bootstrap doesn't depend on spike numbers.
- **M1+ (providers, capture, publish, load, specs)** waits for the spike's decision-gate to produce a strong-pass or conditional-pass result. If the spike failed, the design needs revisiting before more code lands here.

The boundary is clean: stop after the repo is bootstrapped and CI is green on an empty `sg_image_builder/` package, then check spike status before continuing.
**Author:** Architect agent in `SGraph-AI__Service__Playwright` session, 2026-05-11.

---

## Why this doc exists

The brief pack (`README.md` + 11 chapters + 3 appendices) was written assuming a green-field implementation in this fresh repo. Between authoring the pack and your session starting, two things happened:

1. The pack got an **Architect review** that logged five decisions (D1–D5) and nine concerns (A1–A9). Those decisions materially change what you build.
2. A **validation spike** ran in the sister repo (`SGraph-AI__Service__Playwright`) — capturing a working local-claude install, replaying it onto a fresh AL2023 instance, measuring cold-start. That spike's outputs are inputs to your work.

This doc is the meta-layer you read **before** the pack. The pack is your reference manual; this is your orientation.

---

## What you have access to

You have read access to **`SGraph-AI__Service__Playwright`** (the sister-repo where the dev pack itself lives, the Architect review was filed, and the spike ran). Treat it as authoritative reference, not as something to copy wholesale. Specific paths to use are called out throughout this doc — start with §"What you start with" and §"What you can lift from SGraph-AI__Service__Playwright" below.

You **do not** need to clone `SG_Send__Deploy` for v0.1.0. The Twin and `Type__Twin` patterns it contributed are summarised in §"Twin pattern" below; the spike's working code in sister-repo is the concrete reference. Clone `SG_Send__Deploy` only if you hit a Twin-pattern question this doc and the spike code don't answer.

You **do not** need the pre-pack drafts (`v0.27.32__dev-brief__ec2-image-build-cli-s3-first.md`, `v0.27.32__arch-brief__sg-compute-package-manager.md`). The pack supersedes them. Don't go hunting.

---

## What was decided (D1–D5 from the Architect review)

| # | Decision | What this means for you |
|---|---|---|
| **D1** | sgi supersedes the "slim-AMI" approach that was in flight in sister-repo. | Don't be confused if you find references to "slim AMI" or `SPEC-slim-ami-s3-nvme.md` in sister-repo context. That work was capped; sgi replaces it. The slim AMI lives on only as a *base* for sgi to load onto. |
| **D2** | sgi was **developed in `SGraph-AI__Service__Playwright`** during the spike phase, under a parallel `sg_image_builder/` tree, with strict no-touch on existing `sg_compute/` code. | Lift the spike code from there as your **M0 starting point** — don't write the scaffold from scratch. The spike already exercised Storage, Exec_Provider__SSH, capture, S3 publish, and bundle load. See §"What you start with" below. |
| **D3** | No mutation of sg-compute code during the spike. | This constraint **falls away** in your repo — you're not touching sg-compute. But the **interface** to sg-compute via `Exec_Provider__Sg_Compute` is governed by sg-compute's CLI surface, which is partly opaque (no `--json` flags yet). See A6 below. |
| **D4** | The pack lives at `v0.2.8` in sister-repo's version namespace; sgi's own version starts at `v0.0.1`. | Don't carry over the `v0.2.8` label. sgi versions itself; the first release is `v0.1.0` per the pack's M12. The `sg_image_builder/version` file is the authority. |
| **D5** | The spike validated only `vllm_docker` (the local-claude path). The other 8 specs in the ladder are unvalidated. | The pack's spec ladder (M9) is **still right as a sequence** — CPU first, build mileage, GPU last. But the GPU end is already proven; the CPU specs are now validation-of-mechanism, not validation-of-design. Treat them accordingly. |

These decisions are in `team/roles/architect/reviews/05/11/v0.2.8__sgi-brief-pack-acceptance.md` in the sister-repo. Read the long form before starting M1.

---

## What was concerning (A1–A9, condensed)

Read these as "things you must address during implementation, not after". They are not v2 items.

| # | Concern | Action you take |
|---|---|---|
| **A1** | `Exec_Provider__SSH` default trades SSM bugs for keypair/SG-ingress lifecycle bugs. | `providers/aws/EC2__Key_Pair__Lifecycle.py` and `EC2__Security_Group__Ingress.py` MUST be context managers (`__enter__`/`__exit__`) and revoke on body failure. Test with an injected exception in the body — verify the SG ingress is gone. |
| **A2** | `catalog.json` is single-writer; parallel publishes can clobber. | Use S3 conditional PUT (`If-Match` / `If-None-Match`) in `Bundle__Publisher.update_catalog()`. Retry on 412 Precondition Failed. Document in the publisher's docstring. For `Storage__Local_Disk`, atomic rename of a temp file. |
| **A3** | `state.json` has no concurrency guard. | Advisory `flock(2)` on `state.json` in `Workspace__State__Manager`. v1-acceptable; document. |
| **A4** | GPU cold-start budget (90s) is tight given DLAMI's ~37s boot floor. | Verify against spike numbers (§"What the spike produced" below). If spike showed >90s, the KPI in pack §08's vllm_docker section needs a bump before M10 sign-off. |
| **A5** | Strip `minimal` mode is the riskiest part of the pack. | M7 ships **debug-only** for v0.1.0. Mark `Strip__Mode__Minimal` as experimental in code; do not gate any release on it. File a research-brief before attempting full inotify/audit-based access logging. |
| **A6** | `Exec_Provider__Sg_Compute` couples to sg-compute's text output. | Maintain `humans/dinis_cruz/feedback-to-sg-compute.md` (per pack §11) **from the first PR**. Every fallback to text parsing gets logged as a feedback item. Ask the human to relay these to the sg-compute team. |
| **A7** | Sidecar `tests/` overlaps with `sg_image_builder_specs/<spec>/tests/`. **Architect recommendation:** sidecar tests are **bundle-scoped only** ("does this bundle's contents work in isolation"). Spec tests stay in code and are the P16 contract. | Implement accordingly. Add a comment in `Bundle__Sidecar__Builder` documenting the split. |
| **A8** | `Schema__Bundle__Module.modules` is declared-only in v1 — no runtime support. | **Punt the field to v0.2.** Easier to add later than remove. Don't ship dead metadata. |
| **A9** | `Storage` streaming interface doesn't pin chunk size. | **8 MiB chunks** for all three Storage implementations. Match S3 multipart threshold. Document in the Storage interface. |

---

## What the spike produced

> **PLACEHOLDER** — read `team/comms/briefs/v0.2.8__sgi-spike-results.md` in the sister-repo once the spike completes. If that file doesn't exist yet, the spike hasn't finished; you can still do M0 (repo bootstrap) but stop before M1.

Required content here before this handover is "ready":

- **Cold-start p50 / p95** for the local-claude `vllm_docker` path
- **Sub-timings**: `ec2_run_instances`, `ec2_to_ssh_ready`, `bundle_download`, `bundle_extract`, `service_start`, `first_inference`
- **Bundle size on disk** (extracted) and **bundle size in S3** (compressed)
- **Capture wall-clock** (informational — capture runs once)
- **Any surprises** — paths the capture missed, services that didn't start cleanly, NVMe gotchas
- **Spike decision-gate outcome** — strong pass / conditional pass / fail
- **Concrete files in the working capture** — the paths under `/etc`, `/opt`, `/usr/local`, `/var/lib/docker`, the model cache. This is the seed for the production `local_claude` spec's bundle.

Without this section filled in, you don't have measurements to plan against — only predictions. Don't start.

---

## What you start with (the lift)

Once the spike completes, copy these from `SGraph-AI__Service__Playwright`'s `sg_image_builder/` tree. The spike author structured the code to be lift-and-shift-friendly:

```
sg_image_builder/                                          # the package
├── __init__.py                                            # empty
├── version                                                # v0.0.1
├── schemas/
│   ├── storage/Schema__Storage__Object__Info.py
│   ├── exec/Schema__Exec__Request.py
│   ├── exec/Schema__Exec__Result.py
│   └── bundle/Schema__Bundle__Manifest.py
│   └── bundle/Schema__Bundle__File__Entry.py
├── providers/
│   ├── storage/Storage.py                                 # abstract
│   ├── storage/Storage__S3.py
│   ├── storage/Storage__Local_Disk.py
│   ├── storage/Storage__In_Memory.py
│   ├── storage/Storage__Factory.py
│   ├── exec/Exec_Provider.py                              # abstract
│   ├── exec/Exec_Provider__SSH.py
│   └── exec/Exec_Provider__Twin.py
└── spike/                                                 # the spike's one-file driver
    └── run.py                                             # capture | publish | load | bench

tests/sg_image_builder/                                    # the tests
├── unit/                                                  # In_Memory + Twin
└── integration/                                           # Local_Disk round-trips + S3-gated
```

These are **proven against real S3 and a real local-claude instance**. Treat them as load-bearing.

What's **not yet built** (your work, in pack-milestone order):

| Pack milestone | Status post-spike | Your job |
|---|---|---|
| M0 — Repo bootstrap | New — bootstrap in this repo | Set up `pyproject.toml`, CI, `humans/`, `team/`, branch protection (pack §10) |
| M1 — Provider foundations | **Mostly done** by spike. SSH provider, S3, Local_Disk, In_Memory, Twin all working. | Add `Exec_Provider__Sg_Compute`. Add `providers/aws/` helpers as context managers (A1). Add `Storage__Factory.from_uri()`. Polish streaming APIs (A9). |
| M2 — Workspace + CLI | New — spike used a one-file driver, not the typer CLI | Build the typer CLI per pack §03. `Workspace__State__Manager`, `Workspace__Resolver`, target-resolution rules. |
| M3 — Capture + package | **Partially done** — spike captured local-claude. | Generalise: `Capture__Filesystem` (already there) + `Bundle__Packer` + `Bundle__Sidecar__Builder` (new) + the diff/before-after pattern for arbitrary specs. |
| M4 — Publish + load | **Partially done** — spike publishes one bundle, loads it. | Generalise: `Ifd__Path__Builder` (new), `catalog.json` (new, with A2 mitigation), `Bundle__Verifier`, all CLI verbs. |
| M5 — `ssh_file_server` spec | New | This is your **first integration milestone**. Don't skip it because the spike validated vllm_docker — `ssh_file_server` proves the simplified case works (and the strip workflow needs it). |
| M6 — Benchmark | **Partially done** — spike measured manually | Add `Timing__Tracker`, `Benchmark__*` classes, `sgi benchmark *` CLI verbs. |
| M7 — Strip (debug-only) | New | Static keep-list, no test-driven removal. See A5 — don't over-engineer. |
| M8 — Recipes | New | The pack-§08 recipe schema and `Recipe__Executor`. |
| M9 — CPU specs (6 of them) | New | Per the pack ladder. Each spec gets a debrief. |
| M10 — GPU specs | **Mostly done** — spike proved `vllm_docker`. | Promote spike's captured `local_claude` artefact to `vllm_docker` spec. Add `vllm_disk` (non-containerised) as a follow-up. |
| M11 — Events + Kibana | New | Pack §07. Optional in v0.1.0 — `Events__Sink__JSONL` is the v1 default. |
| M12 — zipapp + release | New | `python -m zipapp`, GitHub release, tagged. |

So roughly half of M1, M3, M4, and M10 is **already done** by the time you start. Your effective scope is M0, M2, M5, M6, M7, M8, M9, M11, M12 plus the gaps in the half-done milestones.

---

## Twin pattern (from `SG_Send__Deploy`, summarised)

The pack references `SG_Send__Deploy` for the Twin pattern. The spike's `Exec_Provider__Twin` in sister-repo is your concrete reference. The pattern in shorthand:

```python
# Two parallel class trees:
#
# Schema__Twin                    <-- data only, immutable identity
# ├── Schema__Twin__Config        <-- set once at capture/creation time
# │   └── Schema__Twin__Config__Bundle
# └── Schema__Twin__State         <-- evolves through execute() only
#     └── Schema__Twin__State__Bundle
#
# Type__Twin                      <-- the alive thing with execute()
# └── Type__Twin__Bundle
#     def execute(self, action: Safe_Str, **kwargs):
#         # routes to action__publish, action__verify, etc.
#         # never mutates state.* directly
```

The discipline is: **all state mutations go through `execute()`**, which gives you a free audit trail and the ability to serialise the entire fleet of bundles as one consistent state. If you find yourself writing `self.state.foo = bar` outside an `action__*` method, you're off pattern.

The `Exec_Provider__Twin` (test double that records calls and returns canned responses) follows this pattern. Pack §04 has the full interface; sister-repo's spike implementation is the working reference.

---

## What to read from `SGraph-AI__Service__Playwright`

Since you have read access to the sister-repo, treat these as **first-class references** alongside the pack:

| Path in sister-repo | What's there | When you need it |
|---|---|---|
| `.claude/CLAUDE.md` | The code-discipline rules sgi inherits (Type_Safe, one-class-per-file, empty `__init__.py`, no Pydantic, no boto3 direct, no Literals, 80-char `═══` headers, no docstrings, etc.) | **Required reading before M1.** Most rules apply to sgi unchanged. |
| `team/roles/architect/reviews/05/11/v0.2.8__sgi-brief-pack-acceptance.md` | The Architect review (D1–D5, A1–A9) | **Required reading before M1.** This handover is a digest; the review is the source. |
| `team/comms/briefs/v0.2.8__sgi-local-claude-validation-spike.md` | The spike brief — what was validated, how, and why | **Required reading.** Read it after the pack and before lifting spike code. |
| `team/comms/briefs/v0.2.8__sgi-spike-results.md` | The spike's measured numbers + lessons | **Required before M1.** If absent, the spike hasn't completed yet. |
| `team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md` | EBS lazy-load diagnosis — why sgi exists | Context; read once. |
| `sg_image_builder/` | The spike code you're lifting | **Read every file before copying.** Don't lift blind. |
| `tests/sg_image_builder/` | The spike's test suite — patterns for In_Memory + Twin | **Read before writing new tests.** |
| `sgraph_ai_service_playwright/` | The reference application for the conventions | Look up specific patterns (e.g. how `Type_Safe` is used in a complex schema). |
| `sg_compute/platforms/ec2/user_data/Section__*.py` | The `Section__*` pattern for composing user-data scripts | When you write `Section__Bundle_Fetch` for the load path. Follow the same shape. |
| `team/claude/debriefs/2026-05-11__sg-compute-extend-and-ami-perf.md` | The session debrief preceding sgi's design | Context on `g5.xlarge` quirks, NOPASSWD sudoers, SSM gotchas. Read once. |

The pack itself lives at `library/dev_packs/v0.2.8__sg-image-builder/` in the sister-repo, with this HANDOVER.md at its root. If you have the pack, you already have the path.

---

## First steps (your M0, day 1)

1. Read this doc to the end. Note the open questions in §Open questions.
2. Read pack `README.md` + `00__pack-overview/quick-reference.md`. Skim `01__principles/principles.md`.
3. Confirm with the human: are the §Open questions resolved? If not, ask before writing code.
4. Bootstrap the repo per pack §09 M0:
   - `pyproject.toml`, `requirements.txt`, `requirements-test.txt`
   - Directory structure per pack §02
   - `LICENSE`, `README.md`, `sg_image_builder/version` = `v0.0.1`
   - `.gitignore` per pack §11 (includes `_vaults/`)
   - `_vaults/.gitkeep`
   - `humans/dinis_cruz/{briefs,debriefs}/`
   - `team/roles/{conductor,architect,developer,devops,appsec,librarian}/README.md` per pack §11 template
   - `humans/dinis_cruz/feedback-to-sg-compute.md` with the open items already known (see A6)
5. Set up CI per pack §10 (`pr.yml`, `main.yml`, `tag.yml`). Branch protection on `main` and `dev`.
6. Open the first PR — the bootstrap, with green CI but no sgi code yet.
7. **Then** lift the spike code per §"What you start with". That's PR 2.

After that, you're in the pack's M0–M12 sequence with the adjustments above.

---

## Reading order

Strict order for your first session — don't skip and don't re-order:

**Before M0 (repo bootstrap):**

1. **This doc** (you're here)
2. **Pack `README.md`** — orient on vocabulary
3. **Pack `00__pack-overview/quick-reference.md`** — one-page reference, keep open
4. **Pack `01__principles/principles.md`** — the 21 principles
5. **Pack `02__architecture/architecture.md`** — code layout and boundaries
6. **Pack `09__implementation-plan/implementation-plan.md`** — milestone sequencing, especially M0
7. **Pack `10__dev-ops/dev-ops-brief.md`** — CI workflows, secrets, branch protection
8. **Pack `11__librarian/librarian-brief.md`** — `humans/` + `team/` scaffolding
9. **Sister-repo `.claude/CLAUDE.md`** — the code-discipline rules

**Before M1 (provider foundations onward):**

10. **Sister-repo Architect review** — `team/roles/architect/reviews/05/11/v0.2.8__sgi-brief-pack-acceptance.md`
11. **Sister-repo spike brief** — `team/comms/briefs/v0.2.8__sgi-local-claude-validation-spike.md`
12. **Sister-repo spike results** — `team/comms/briefs/v0.2.8__sgi-spike-results.md` (if absent, spike hasn't completed; stop here)
13. **Pack `04__providers/providers.md`** — the abstractions everything else builds on
14. **Sister-repo `sg_image_builder/` and `tests/sg_image_builder/`** — read every file before lifting

**On demand (when you start the milestone):**

- Pack `03__cli/cli-surface.md` → M2
- Pack `05__bundles/bundles-and-storage-layout.md` → M4 (refine pack details)
- Pack `07__test-and-benchmark/test-and-benchmark.md` → M6
- Pack `06__strip/strip-workflow.md` → M7 (debug-only, per A5)
- Pack `08__specs-and-recipes/specs-and-recipes.md` → M5 and beyond
- Pack appendices → reference, look up as needed
- Sister-repo `sg_compute/platforms/ec2/user_data/Section__*.py` → when you write `Section__Bundle_Fetch`

---

## Open questions to confirm with the human before starting

1. **Repo setup state.** Is `SG-Compute/SG-Compute__Image-Builder` already created? Empty? Are AWS secrets configured for E2E?
2. **Spike outcome.** Did the spike strong-pass, conditional-pass, or fail? §"What the spike produced" needs to be filled in before you start.
3. **Which specs land in v0.1.0 vs v0.2?** The pack assumes all 9. Given the spike validated `vllm_docker` directly, is `vllm_disk` (non-containerised GPU) a v0.1.0 deliverable, or v0.2? Likewise `ollama_*` — included or deferred?
4. **Should `Exec_Provider__Sg_Compute` ship in v0.1.0 at all?** If you can launch fresh instances via `Exec_Provider__SSH` directly, the Sg_Compute provider is only useful for dog-fooding (running sgi against an `sg lc` instance). Skipping it lets you ignore A6 entirely for v0.1.0.
5. **Branch model in this repo.** Pack §10 says `main` + `dev` with feature branches off `dev`. Confirm — sister-repo uses `dev` as primary; some teams skip `dev` and use `main` only.
6. **Where does `feedback-to-sg-compute.md` get its initial content?** The sister-repo will accumulate items during the spike. Should those be pre-populated when you bootstrap, or start empty and rebuild from the spike's debrief?
7. **Is there a release timeline?** The pack estimates ~5 weeks for v0.1.0 solo or ~3.5 weeks with parallelism. If there's an external deadline, milestone sequencing might change (e.g. ship vllm_docker-only as v0.1.0 and defer the ladder).

---

## What to do if the spike failed

Don't start v0.1.0. The spike's role is to prove the capture/replay approach beats the existing 10-minute cold-start. If it didn't:

- Read the spike's debrief carefully — which step blew the budget?
- File a brief at `humans/dinis_cruz/briefs/<date>/v0.1.0__post-spike-redesign.md` with the failure modes and proposed corrections.
- Hold on the v0.1.0 implementation until a follow-up spike validates the corrections.

The pack may need re-issuing as v0.2.x if the failure was design-deep. That's an Architect call, not a Dev call.

---

## What success looks like

When you ship `v0.1.0`:

- All 9 specs (or whichever subset survives §Open question 3) pass their E2E tests on real AWS.
- `sgi test run vllm_docker --launch` matches or beats the spike's measured cold-start (no regression vs spike).
- The zipapp downloads and runs as a single file with Python 3.11+.
- Air-gap workflow proven: `sgi storage migrate s3://... file:///mnt/usb/` produces a complete portable registry, and `sgi bundle load` works from that registry.
- All 21 principles honoured in code review.
- `humans/dinis_cruz/feedback-to-sg-compute.md` has been periodically reviewed; high-priority items have been relayed to the sg-compute team.

The headline number is the cold-start: **local-claude from ~600s to ≤120s p50**. If `v0.1.0` ships that, sgi is justified.

End of handover.
