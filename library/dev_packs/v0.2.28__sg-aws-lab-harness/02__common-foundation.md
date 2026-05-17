---
title: "02 — Common foundation (must land first)"
file: 02__common-foundation.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 02 — Common foundation

**Everything in this file must land in a single PR before any of Sonnet Agents A-E starts.** Without it, the per-agent slices have no harness to plug into.

Owner: a single dedicated "foundation" PR — call it **Agent 0** (Sonnet, Opus-reviewed). Size: ~1 day. Out of the ~7800-line total, the foundation is ~1500 lines of scaffolding that the other slices then fill in.

---

## 1. Scope of the foundation PR

Production code (all under `sgraph_ai_service_playwright__cli/aws/lab/`):

### `cli/`

- `Cli__Lab.py` — Typer surface skeleton with **all top-level verbs** (`list`, `show`, `run`, `runs {list,show,diff}`, `sweep`, `account {show,set-expected}`, `ledger {show,replay}`, `serve`). `serve`, `runs diff` and renderer-dependent paths return `not-implemented` errors that the per-agent PRs fill in — but the verb tree shape is locked here so agents A-E don't fight over `Cli__Lab.py` merge conflicts.

### `service/`

- `Lab__Runner.py` — the orchestrator. Methods:
  - `start(experiment)` — account guard + ledger open + signal handlers
  - `teardown()` — iterate ledger via `teardown_dispatcher`
  - `abort(reason)`
  - `create_and_register(...)` — the create+register pairing helper (`lab-brief/04 §1.3`)
  - `now_iso() / stopwatch(label) / log(...)`
  - client accessors `r53() / cf() / lambda_() / dig() / authoritative_checker() / public_resolver_checker()` — return the real client if it exists, or the `Lab__*__Client__Temp` if not
- `Lab__Ledger.py` — append-only JSONL writer/reader with file locking
- `Lab__Sweeper.py` — tag-driven discovery + delete. R53 / CF / Lambda / ACM / EC2 / SSM / IAM resource scanners; CLI driver in `Cli__Lab.py sweep`
- `Lab__Tagger.py` — centralised application of the five required tags (`sg:lab`, `sg:lab:run-id`, `sg:lab:experiment`, `sg:lab:expires-at`, `sg:lab:created-by`)
- `Lab__Safety__Account_Guard.py` — refuses to run if `SG_AWS__LAB__EXPECTED_ACCOUNT_ID` is set and doesn't match `sts.get_caller_identity()`
- `Lab__Timing.py` — `perf_counter` wrapper, ISO timestamps, duration helpers
- `teardown/Lab__Teardown__Dispatcher.py` — maps `Enum__Lab__Resource_Type` → teardown fn
- `teardown/Lab__Teardown__R53.py` — full implementation (DNS is the only mutating surface in P1)
- `teardown/Lab__Teardown__{CF,Lambda,ACM,EC2,SSM,IAM}.py` — **stub files that raise `NotImplementedError`**. Agents B/C/D fill these in for their slices.
- `experiments/Lab__Experiment.py` — abstract base (`name`, `tier`, `budget_seconds`, `budget_resources`, `execute()`, `metadata()`)
- `renderers/Render__Table.py` — Rich-based table renderer (every result schema renderable as a table)
- `renderers/Render__JSON.py` — pretty JSON dump
- `temp_clients/__init__.py` — empty; per-agent PRs add `Lab__CloudFront__Client__Temp.py` (Agent C) and `Lab__Lambda__Client__Temp.py` (Agent B)

### `schemas/` (per-class files)

Foundation schemas (every per-agent PR adds its own `Schema__Lab__Result__*` later):

- `Schema__Lab__Ledger__Entry.py`
- `Schema__Lab__Run__Result.py`
- `Schema__Lab__Experiment__Metadata.py`
- `Schema__Lab__Timing__Sample.py`
- `Schema__Lab__Sweep__Report.py`
- `Schema__Lab__Account__Identity.py`

### `enums/` (per-class files)

- `Enum__Lab__Resource_Type.py` — `R53_RECORD | CF_DISTRIBUTION | LAMBDA | LAMBDA_URL | ACM_CERT | EC2_INSTANCE | SG | IAM_ROLE | SSM_PARAM`. Each value carries `teardown_order` (10, 20, 30, ...).
- `Enum__Lab__Entry__State.py` — `PENDING | DELETED | FAILED | ABANDONED | DELETED_PENDING_CF_DISABLE`
- `Enum__Lab__Tier.py` — `READ_ONLY | MUTATING_LOW | MUTATING_HIGH`
- `Enum__Lab__Tag__Key.py` — the five tag keys
- `Enum__Lab__Experiment__Status.py` — `PENDING | RUNNING | OK | FAILED | TIMEOUT | ABORTED`

### `primitives/` (per-class files)

- `Safe_Str__Lab__Run_Id.py` — pattern `<iso-ts-z>__<6-char-nonce>`
- `Safe_Str__Lab__Entry_Id.py` — uuid4 hex
- `Safe_Str__Lab__Resource_Id.py` — opaque AWS-side id
- `Safe_Str__Lab__Experiment_Name.py` — e.g. `"propagation-timeline"`
- `Safe_Str__Timestamp.py` — ISO 8601 UTC
- `Safe_Int__Duration_Ms.py`

### `collections/` (per-class files)

- `List__Schema__Lab__Ledger__Entry.py`
- `List__Schema__Lab__Timing__Sample.py`

### Experiment registry

- `service/experiments/registry.py` — module-level dict + helper functions (`get_experiment(name) -> Lab__Experiment`, `list_experiments() -> List[…__Metadata]`). This is the **one** allowed `*_registry.py` exception (CLAUDE.md rule #21). Each per-agent PR appends its experiment entries.

---

## 2. Top-level wiring

- In `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py`, add:

  ```python
  from sgraph_ai_service_playwright__cli.aws.lab.cli.Cli__Lab import lab_app
  ...
  app.add_typer(lab_app, name='lab')
  ```

  alongside the existing `dns`, `acm`, `billing`, `cf`, `iam` mounts. Lambda is the dynamic-group exception and is unchanged.

- `.gitignore` — add `.sg-lab/` so ledger / runs / state never get committed.

- `library/catalogue/02__cli-packages.md` and `library/catalogue/08__aws-and-infrastructure.md` — add the new `aws/lab/` package entry. (Librarian task; the foundation PR includes the doc edit so the catalogue stays in sync.)

---

## 3. Tests in the foundation PR

Under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/`:

- `test_Lab__Ledger.py` — write/read/replay round-trip; partial-write recovery; concurrent writers (file lock)
- `test_Lab__Tagger.py` — every taggable resource type gets all five required tags
- `test_Lab__Safety__Account_Guard.py` — in-memory STS, matches and mismatches
- `test_Lab__Sweeper.py` — in-memory `*__AWS__Client` returning tagged + untagged resources; sweeper deletes only those with the full tag set
- `test_Lab__Runner__In_Memory.py` — runs a no-op experiment; asserts ledger lifecycle (start → execute → teardown)
- `test_Cli__Lab.py` — Typer-based smoke: `list` (empty registry), `show` (404), `run` (not-implemented), `sweep` (no resources), `account show`

**No mocks, no patches.** Use `register_playwright_service__in_memory()`-style in-memory composition (CLAUDE.md testing rule #1).

Acceptance for the foundation PR:

```bash
sg aws lab --help                                                     # full verb tree
sg aws lab account show                                               # STS + region
sg aws lab list                                                       # empty list (no experiments yet)
sg aws lab sweep                                                      # "no leaked resources"
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run nonexistent             # clean error
```

Plus `pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/ -v` passes.

---

## 4. The three-layer safety story (lock this in foundation)

Three independent cleanup mechanisms + a session-level sweeper. **Any one mechanism failing should not leak.** (Full design: `lab-brief/04`.)

| Layer | Mechanism | Covers |
|------:|-----------|--------|
| 1 | Synchronous teardown in `try/finally` around `experiment.execute()` | Happy path; experiment-raises path |
| 2 | `atexit` + SIGINT + SIGTERM handlers calling `_teardown_synchronous` | Ctrl-C; `kill <pid>`; soft exits |
| 3 | `sg aws lab sweep [--apply]` — tag-driven discovery + delete | SIGKILL; hard reboot; corrupt ledger |
| 4 | `sg:lab:expires-at` tag with default 1 h TTL — sweeper deletes anything past expiry regardless of ledger state | All-layers-failed worst case (1 h × N concurrent runs of orphan resources) |

The foundation PR delivers layers 1, 2, and the sweeper *framework* for layer 3. Per-agent PRs plug their resource type into `Lab__Sweeper` + their `Lab__Teardown__*` implementation.

### Teardown order (locked)

Encoded in `Enum__Lab__Resource_Type.teardown_order`:

| Order | Resource | Why |
|------:|----------|-----|
| 10 | CF distribution (disable then delete) | Slowest; must finish before upstream Lambda/cert |
| 20 | Route 53 ALIAS to a CF distribution | Cannot delete CF before its alias is gone |
| 30 | Route 53 A records (non-alias) | Independent |
| 40 | Lambda Function URL | Must go before the function |
| 50 | Lambda function | Independent after URL gone |
| 60 | ACM cert (lab-minted only) | Only safe once nothing references it |
| 70 | EC2 instance (lab-tagged only) | Independent |
| 80 | Security groups (lab-tagged only) | After the EC2 |
| 90 | SSM parameters | Cheap; last |
| 100 | IAM roles | Need attachments removed first |

CloudFront delete is **asynchronous** — the ledger entry transitions to `DELETED_PENDING_CF_DISABLE` and the next `sg aws lab sweep` finishes the deletion when the distribution reaches `Disabled + Deployed`. (~15-25 min after disable.) This is the one case where the harness leaves something behind; it's an "in-flight" leave-behind, not a leak.

### Defensive sweeper

The sweeper **only** deletes resources where ALL of `sg:lab=1`, `sg:lab:run-id`, `sg:lab:expires-at` are present. Resources missing any of these tags are ignored even if they match a name pattern. This is the most important safety rule — it makes the sweeper defensive against itself.

---

## 5. Why the foundation must come first

Each per-agent PR depends on:

- `Lab__Runner.create_and_register(...)` — the resource-pairing helper
- `Schema__Lab__Run__Result` — every experiment returns one
- `Lab__Experiment` — the abstract base every experiment extends
- The teardown dispatcher — every per-agent PR registers a teardown fn for its resource type
- `Render__Table` — every result schema needs to render to a Rich table
- `service/experiments/registry.py` — every experiment registers in here

If these are not stable before agents A-E start, every PR fights every other PR for the same files. Landing the foundation first means each per-agent PR adds **new files in its own sub-folder** plus a single registration line in `registry.py`.

---

## 6. What the foundation PR **does not** include

- No experiments. Empty `experiments/dns/`, `experiments/cf/`, `experiments/lambda_/`, `experiments/transition/`.
- No `Render__Timeline__ASCII`, `Render__Histogram__ASCII`, `Render__HTML` — Agent E and per-agent PRs add these.
- No `runs diff` implementation — Agent E.
- No `serve` implementation — Agent E.
- No `Lab__Teardown__{CF,Lambda,ACM,EC2,SSM,IAM}.py` filled in — they're stubs raising `NotImplementedError`. Per-agent PRs implement.
- No in-tree lab Lambda functions — Agent B brings these.
- No `Lab__*__Client__Temp` boto3 wrappers — Agents B and C bring these.

Keeping these out of the foundation keeps the foundation PR reviewable in one pass.

---

## 7. Foundation PR sign-off checklist

Before merging the foundation PR:

- [ ] `sg aws lab --help` shows the full verb tree
- [ ] `sg aws lab list` returns an empty list cleanly
- [ ] `sg aws lab sweep` reports "no leaked resources" against the live account
- [ ] `sg aws lab account show` prints STS caller identity
- [ ] `Lab__Runner.create_and_register(...)` writes ledger entry *before* invoking the factory (verified by test)
- [ ] `Lab__Sweeper` refuses to delete a resource missing any of the three required tags (verified by test)
- [ ] `.sg-lab/` is in `.gitignore`
- [ ] `library/catalogue/02__cli-packages.md` and `library/catalogue/08__aws-and-infrastructure.md` mention `aws/lab/`
- [ ] No `boto3` import outside the (stubbed) `temp_clients/` folder

Once these are green, fire Agents A-E in parallel.
