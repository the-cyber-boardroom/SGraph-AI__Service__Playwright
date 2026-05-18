---
title: "02 — Common foundation (must land first)"
file: 02__common-foundation.md
author: Architect (Claude)
date: 2026-05-17 (rev 3 — after v0.2.29 _shared/ landed)
parent: README.md
---

# 02 — Common foundation

**Everything in this file must land in a single PR before any of Sonnet Agents A-E starts.** Without it, the per-agent slices have no harness to plug into.

Owner: a single dedicated "foundation" PR — call it **Agent 0** (Sonnet, Opus-reviewed). Size: ~0.75 day (down from rev 2's ~1 day because v0.2.29's `_shared/` provides ~30% of the plumbing). Foundation is ~1000 lines of lab-specific scaffolding on top of `_shared/`.

---

## 0. What the lab inherits from `sgraph_ai_service_playwright__cli/aws/_shared/` (v0.2.29)

The lab is built **on top of** the shared AWS scaffold that landed in v0.2.29. Per Decision #9, do NOT reinvent any of:

| `_shared/` artefact | Lab uses it for |
|---------------------|-----------------|
| `Mutation__Gate.py` — `@require_mutation_gate(env_var)` decorator | Every mutating `sg aws lab` verb gets `@require_mutation_gate('SG_AWS__LAB__ALLOW_MUTATIONS')` |
| `Aws__Confirm.py` — `confirm_or_abort(msg, yes, dry_run)` | Lab's `--yes` / `--dry-run` UX; Tier-2 `--tier-2-confirm` wraps this |
| `Aws__Tagger.py` — `tags_for(surface, verb, session_id) -> List__Schema__AWS__Tag` | Base for `Lab__Tagger` (adds `sg:lab:*` keys on top of the canonical 5 `sg:*` tags) |
| `Aws__Region__Resolver.py` — 6-tier precedence (env / role / config / etc.) | `Lab__Runner` region resolution |
| `source_contract/Source__Contract.py` (ABC) + companion types | `Lab__Source__Adapter` implements this so lab read-only experiments appear in `sg aws observe sources` |
| `primitives/Safe_Str__AWS__{ARN,Region,Account_Id,Role__ARN,Tag_Key,Tag_Value}` | Reused directly in lab schemas |
| `schemas/Schema__AWS__{Tag,ARN,Resource__Reference,Source__Event}` | Reused directly; lab schemas compose these |
| `collections/List__Schema__AWS__{Tag,Source__Event}` | Reused directly |
| `enums/Enum__AWS__{Surface,Mutation__Tier}` | `Enum__Lab__Tier` **aligns with** `Enum__AWS__Mutation__Tier` — same three values (READ_ONLY / MUTATING_LOW / MUTATING_HIGH). Use the shared enum; do not redeclare. |

If a lab schema needs e.g. a `tag_key` field, it uses `Safe_Str__AWS__Tag_Key` from `_shared/primitives/` — not a new `Safe_Str__Lab__Tag_Key`. The lab adds new primitives ONLY for lab-specific concepts (`Safe_Str__Lab__Run_Id`, `Safe_Str__Lab__Experiment_Name`, etc.).

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
  - client accessors `r53() / cf() / lambda_() / dig() / authoritative_checker() / public_resolver_checker()` — return the existing `*__AWS__Client` from `aws/<svc>/service/`. For P0+P1 only `r53()`, `dig()`, and the two resolver checkers are wired in foundation. `cf()` and `lambda_()` raise `Lab__Phase__Not_Ready__Error` until v2 vault-publish 2a/2b ship the expanded primitives — see decision #2.
- `Lab__Ledger.py` — append-only JSONL writer/reader with file locking
- `Lab__Sweeper.py` — tag-driven discovery + delete. R53 / CF / Lambda / ACM / EC2 / SSM / IAM resource scanners; CLI driver in `Cli__Lab.py sweep`. **Reuses v0.2.29 surfaces:** EC2 sweep via `EC2__AWS__Client.list_instances(tag_filters=...)`; S3 sweep (if used) via `S3__AWS__Client`; IAM role sweep can leverage `Iam__Graph__Builder` for graph-aware cleanup.
- `Lab__Tagger.py` — **thin extension of `_shared/Aws__Tagger`**. Adds `sg:lab` + `sg:lab:run-id` + `sg:lab:experiment` + `sg:lab:expires-at` + `sg:lab:created-by` on top of the canonical 5 `sg:*` tags. Returns the same `List__Schema__AWS__Tag` type.
- `Lab__Safety__Account_Guard.py` — refuses to run if `SG_AWS__LAB__EXPECTED_ACCOUNT_ID` is set and doesn't match `sts.get_caller_identity()`. The STS call goes through `Sg__Aws__Session.from_context()` so it inherits any role configured by the operator.
- `Lab__Timing.py` — `perf_counter` wrapper, ISO timestamps, duration helpers
- `Lab__Phase__Not_Ready__Error.py` — exception raised by `Lab__Runner.cf()` / `lambda_()` accessors when their gating v2 phase hasn't shipped yet. One-line exception class subclassing `Exception`.
- `Lab__Source__Adapter.py` — implements `Source__Contract` from `_shared/source_contract/`. Surfaces lab read-only experiments to `sg aws observe`. For each lab experiment with `tier == READ_ONLY`, registers a source named `lab:<experiment-name>` so `sg aws observe sources` lists them and `sg aws observe tail lab:resolver-latency` streams results. **Per Decision #10.**

  **Registration MUST be lazy** — `Lab__Source__Adapter.register_all(source_registry)` is called only from two places: (a) the `sg aws lab` Typer top-level `callback()` (so listing experiments populates the registry), and (b) `sg aws observe`'s own `Source__Registry` discovery hook (so `sg aws observe sources` sees lab sources). It is NOT called at module-import time. This means an operator running e.g. `sg aws dns zones list` pays zero import-time cost for the lab's source registrations.
- `teardown/Lab__Teardown__Dispatcher.py` — maps `Enum__Lab__Resource_Type` → teardown fn
- `teardown/Lab__Teardown__R53.py` — full implementation (DNS is the only mutating surface in P1)
- `teardown/Lab__Teardown__{CF,Lambda,ACM,EC2,SSM,IAM}.py` — **stub files that raise `NotImplementedError`**. Agents B/C/D fill these in for their slices.
- `experiments/Lab__Experiment.py` — abstract base. Per delta `B.2`, the runner is injected as a field at `setup()` time (Type_Safe field assignment), not passed into `execute(runner)` per call. Attributes: `name`, `tier`, `budget_seconds`, `budget_resources`; methods: `setup() -> Self`, `execute() -> Schema__Lab__Run__Result`, `metadata() -> Schema__Lab__Experiment__Metadata`.
- `renderers/Render__Table.py` — Rich-based table renderer (every result schema renderable as a table)
- `renderers/Render__JSON.py` — pretty JSON dump
- **(no `temp_clients/` folder)** — per rev 2 decision #2.

### `schemas/` (per-class files) — lab-specific only; reuse `_shared/schemas/` for anything AWS-generic

Foundation schemas (every per-agent PR adds its own `Schema__Lab__Result__*` later):

- `Schema__Lab__Ledger__Entry.py` — references `_shared/Schema__AWS__Resource__Reference` for `resource_id` field
- `Schema__Lab__Run__Result.py` — composes `_shared/Schema__AWS__Tag` for the tag list
- `Schema__Lab__Experiment__Metadata.py`
- `Schema__Lab__Timing__Sample.py`
- `Schema__Lab__Sweep__Report.py`
- `Schema__Lab__Account__Identity.py` — references `_shared/Safe_Str__AWS__Account_Id` and `Safe_Str__AWS__ARN`

### `enums/` (per-class files) — lab-specific only

- `Enum__Lab__Resource_Type.py` — `R53_RECORD | CF_DISTRIBUTION | LAMBDA | LAMBDA_URL | ACM_CERT | EC2_INSTANCE | SG | IAM_ROLE | SSM_PARAM | S3_BUCKET`. Each value carries `teardown_order` (10, 20, 30, ...). (S3_BUCKET added in rev 3 since v0.2.29 ships S3 support and the lab may need S3 storage for the lab Lambda's body-size experiment.)
- `Enum__Lab__Entry__State.py` — `PENDING | DELETED | FAILED | ABANDONED | DELETED_PENDING_CF_DISABLE`
- `Enum__Lab__Experiment__Status.py` — `PENDING | RUNNING | OK | FAILED | TIMEOUT | ABORTED`
- **`Enum__Lab__Tag__Key.py` — DELETED.** The 5 canonical `sg:*` tag keys live in `_shared/primitives/Safe_Str__AWS__Tag_Key.py` already; lab adds its `sg:lab:*` keys as instances of that primitive, not a new enum.
- **`Enum__Lab__Tier.py` — DELETED.** Use `_shared/enums/Enum__AWS__Mutation__Tier` directly (same three values).

### `primitives/` (per-class files) — lab-specific only

- `Safe_Str__Lab__Run_Id.py` — pattern `<iso-ts-z>__<6-char-nonce>`
- `Safe_Str__Lab__Entry_Id.py` — uuid4 hex
- `Safe_Str__Lab__Experiment_Name.py` — e.g. `"propagation-timeline"`
- `Safe_Int__Duration_Ms.py`
- **`Safe_Str__Lab__Resource_Id.py` — DELETED.** Use `_shared/Safe_Str__AWS__ARN` or the existing per-service id primitives (`Safe_Str__Hosted_Zone_Id` from `dns/`, `Safe_Str__Lambda__Arn` from `lambda_/`, etc.).
- **`Safe_Str__Timestamp.py` — DELETED.** Use `_shared/primitives/Safe_Str__Iso8601_Timestamp` if it exists; otherwise add to `_shared/` (PR against the shared package), not to lab.

### `collections/` (per-class files)

- `List__Schema__Lab__Ledger__Entry.py`
- `List__Schema__Lab__Timing__Sample.py`
- (lab does NOT need its own `List__Schema__AWS__Tag` — use `_shared/collections/` for that.)

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

  alongside the existing `dns`, `acm`, `billing`, `cf`, `iam` mounts. Lambda is the dynamic-group exception and is unchanged. Mount order per delta `B.6`: `dns`, `acm`, `billing`, `cf`, `iam`, `lab`.

- `.gitignore` — add `.sg-lab/` so ledger / runs / state never get committed.

- **Catalogue + reality-doc updates** (Librarian-style — same PR):
  - `library/catalogue/cli.md` — add `sg aws lab` entry (8-shard layout; old `02__cli-packages.md` is archived under `library/catalogue/_archive/`).
  - `library/catalogue/infra.md` — add the lab tag/sweep AWS surface entry (old `08__aws-and-infrastructure.md` is archived).
  - `team/roles/librarian/reality/cli/` (domain tree) — add `sg aws lab` to the per-domain `index.md`. The old `team/roles/librarian/reality/v0.1.31/` monoliths are archived (`team/roles/librarian/reality/_archive/`); do not edit them.

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
- **No `Lab__*__Client__Temp` boto3 wrappers** (rev 2) — see decision #2. Agents B / C use the existing `*__AWS__Client` classes once v2 phases 2a/2b ship the expansions.

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
- [ ] `library/catalogue/cli.md` and `library/catalogue/infra.md` mention `aws/lab/`; corresponding `team/roles/librarian/reality/cli/index.md` updated (per the rolling pattern set by the v0.2.29 slice debriefs)
- [ ] **No `boto3` import in `aws/lab/`** — every AWS call goes through an existing `aws/<svc>/service/*__AWS__Client`. `Lab__Safety__Account_Guard` calls STS via `Sg__Aws__Session.from_context()`.
- [ ] **No reinvented primitives / schemas / enums** — `_shared/` is imported where it applies. `git grep -E "Safe_Str__Lab__(Tag_Key|Resource_Id|Timestamp)" aws/lab/` returns empty.
- [ ] `Lab__Tagger` extends `Aws__Tagger.tags_for(...)`; does not duplicate the canonical 5 `sg:*` tags
- [ ] Every mutating `sg aws lab` verb is decorated with `@require_mutation_gate('SG_AWS__LAB__ALLOW_MUTATIONS')` from `_shared/Mutation__Gate.py`
- [ ] Mutating experiments use `confirm_or_abort(...)` from `_shared/Aws__Confirm.py` for `--yes`/`--dry-run`; Tier-2 wraps this with the extra `--tier-2-confirm` check
- [ ] `Lab__Source__Adapter` implements `Source__Contract` and registers every `READ_ONLY` experiment with `sg aws observe`'s `Source__Registry` (Decision #10)

Once these are green, fire Agents A and E in parallel (no v2 dependency). Agents B and C wait for v2 phases 2b/2a respectively. Agent D waits for B + C.

---

## 8. Platform note — keyring dependency

`Sg__Aws__Session.from_context()` (used everywhere per decision #6) internally instantiates `Keyring__Mac__OS()` which calls `/usr/bin/security` — **macOS only**. On Linux (CI workers, container hosts), the keyring call returns an error and `from_context()` falls through to bare `boto3.client(service)` with no role set.

**Implication for the lab:**

- **Local dev (macOS operator)** — role-aware credentials work; `sg --as lab ...` honoured.
- **Linux CI / container hosts** — falls through to whatever the AMI/container's default boto3 credential chain provides (env vars, IMDS, `~/.aws/credentials`). The audit-log integration and CloudTrail-correlatable session names are not active in that mode.

For lab integration tests gated by `SG_AWS__LAB__ALLOW_MUTATIONS=1` running on Linux, the operator must supply credentials via the standard boto3 chain. This is acceptable for the foundation — but the v0.2.28 credentials plan §"Anti-scope" item "Cross-platform keyring (Linux Secret Service, Windows Credential Manager)" tracks the longer-term fix.

The foundation PR must document this loudly in the `Cli__Lab.py` top-level `--help` text and in `Lab__Safety__Account_Guard` so an operator on Linux doesn't think the role system is broken.
