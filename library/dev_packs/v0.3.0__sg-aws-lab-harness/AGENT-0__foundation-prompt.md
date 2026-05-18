---
title: "Agent 0 — Foundation PR — Sonnet implementation prompt"
file: AGENT-0__foundation-prompt.md
author: Architect (Claude Opus 4.7)
date: 2026-05-18
parent: README.md
audience: Sonnet (taking over this session for implementation)
status: READY-TO-EXECUTE
---

# Agent 0 — Foundation PR — Sonnet implementation prompt

This is the self-contained briefing for the Sonnet sub-agent that will implement the **Foundation PR** for the `sg aws lab` measurement harness, on the current branch `claude/aws-primitives-support-NVyEh`.

The Architect (Opus 4.7) has shipped the briefing pack in three revisions; rev 3 is current. Your job is to implement what's in `02__common-foundation.md` — nothing more, nothing less.

---

## Role and scope

**You are Dev (Sonnet) working on the SG Playwright Service.**

You are implementing **Slice 0 — Foundation** of the v0.3.0 `sg aws lab` milestone. This is the scaffold that the five per-agent Sonnet slices (A–E) will later plug into. After this PR lands, the lab harness will have:

- A complete `sg aws lab` Typer verb tree (mostly stubbed verbs at this stage)
- A working `Lab__Runner` + `Lab__Ledger` + `Lab__Sweeper` + `Lab__Tagger` + `Lab__Safety__Account_Guard`
- The full safety story (3 cleanup layers + TTL-stamped tags + sweeper)
- A `Lab__Source__Adapter` skeleton so lab read-only experiments can later register as `sg aws observe` sources
- Stub `Lab__Teardown__{CF,Lambda,ACM,EC2,SSM,IAM}.py` (raise `NotImplementedError` — agents B/C/D fill these in)
- Full implementation of `Lab__Teardown__R53.py` (DNS-only mutations are the only thing P0+P1 will do)
- Wire-up into `aws/cli/Cli__Aws.py`, `.gitignore`, `library/catalogue/cli.md`, `library/catalogue/infra.md`, `team/roles/librarian/reality/cli/index.md`
- A passing unit-test suite under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/`

**You do NOT implement any experiment.** Agents A–D do that in subsequent PRs. `service/experiments/dns/`, `service/experiments/cf/`, `service/experiments/lambda_/`, `service/experiments/transition/` stay empty. `service/experiments/Lab__Experiment.py` (the abstract base) is in scope; specific `Lab__Experiment__*` classes are NOT.

---

## Required reading (in order)

You have NOT seen the conversation that produced this brief. Read the following BEFORE writing any code. Each file is small enough to fully read.

```
1.  /.claude/CLAUDE.md
        Project rules (Type_Safe, no Pydantic, no Literals, one-class-per-file,
        empty __init__.py, no docstrings, 80-char ═══ headers in Python).

2.  library/dev_packs/v0.3.0__sg-aws-lab-harness/README.md
        Pack-level overview, 10 locked decisions, status of 15 open Qs, sign-off
        checklist. NOTE the "Why this revision exists" section — you are working
        on rev 3 of the pack.

3.  library/dev_packs/v0.3.0__sg-aws-lab-harness/01__scope-and-architecture.md
        Module shape, primitive dependencies, v0.2.29 inheritance.

4.  library/dev_packs/v0.3.0__sg-aws-lab-harness/02__common-foundation.md
        THIS IS YOUR SPEC. Every file, schema, enum, primitive, test, and
        sign-off item listed here belongs to this PR.

5.  team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md
        Read §B.1 through §B.7 — non-negotiable corrections that override
        the lab-brief's shape. The most important ones:
          B.1: no Set__Str — use Type_Safe__Dict / Type_Safe__List subclasses
          B.2: Lab__Experiment.execute() takes NO runner argument; the runner
               is injected as a field at setup() time
          B.3: file names match class names exactly — NO E01__ numeric prefix
          B.4: no Dict__Str__Str / Dict__Str__Int — use Type_Safe__Dict__Safe_Str__*
               collection subclasses with their own files under collections/
          B.7: lab safety story stays in lab — do NOT generalise the ledger
               pattern into other surfaces

6.  library/guides/v3.63.4__type_safe.md
        Type_Safe rules — kwargs_to_self, forbidden patterns, no Pydantic.

7.  library/guides/v3.63.4__python_formatting.md
        80-char ═══ headers, inline comments only, no docstrings.

8.  library/guides/v3.28.0__safe_primitives.md
        How to declare Safe_* primitives.

9.  library/guides/v3.63.3__collections_subclassing.md
        How to declare List__* / Dict__* subclasses.

10. library/guides/v3.1.1__testing_guidance.md
        no-mocks rule, *__In_Memory pattern, context managers.

11. team/claude/debriefs/2026-05-17__v0.2.29-sg-aws-primitives-expansion.md
        What v0.2.29 shipped. Read §3.1 "Foundation" to understand the
        _shared/ scaffold you'll be reusing.
```

After reading the above, **list every file under `sgraph_ai_service_playwright__cli/aws/_shared/`** so you know what's there to reuse. The lab inherits substantially from `_shared/` — do not reinvent any of it.

---

## Constraints (non-negotiable)

These are repeated from the pack for visibility. Re-read them before each commit.

| Rule | Where it bites |
|------|----------------|
| **Type_Safe everywhere** | every class. No Pydantic, no `dataclass`, no plain Python classes for data. |
| **One class per file** | every `Safe_*`, `Enum__*`, `Schema__*`, `List__*`, `Dict__*`. Module name = class name. |
| **Empty `__init__.py`** | never put re-exports in `__init__.py`. Callers import the per-class fully-qualified path. |
| **No Literals** | use `Enum__*`. |
| **No raw primitives in schemas** | no `str`/`int`/`list`/`dict`/`set` as Type_Safe attributes. Use `Safe_Str__*`, `Safe_Int__*`, `Type_Safe__Dict__*`, `Type_Safe__List__*`, `Enum__*`. (`bool` is allowed.) |
| **No docstrings** | inline `# comment` only. Align to the right of code; `═══` section headers in Python. |
| **No `boto3` import inside `aws/lab/`** | `Lab__Safety__Account_Guard` calls STS via `Sg__Aws__Session.from_context()`. Every other AWS call routes through an existing `aws/<svc>/service/*__AWS__Client`. |
| **Reuse `_shared/` aggressively (Decision #9)** | `Lab__Tagger` extends `Aws__Tagger`; mutation gates use `@require_mutation_gate('SG_AWS__LAB__ALLOW_MUTATIONS')`; confirm prompts use `confirm_or_abort(msg, yes, dry_run)`; primitives like `Safe_Str__AWS__Tag_Key`, `Safe_Str__AWS__ARN`, `Safe_Str__AWS__Account_Id` come from `_shared/primitives/`; schemas like `Schema__AWS__Tag`, `Schema__AWS__Resource__Reference` come from `_shared/schemas/`. **Do NOT create:** `Enum__Lab__Tier` (use `Enum__AWS__Mutation__Tier`), `Enum__Lab__Tag__Key`, `Safe_Str__Lab__Resource_Id` (use `Safe_Str__AWS__ARN`), `Safe_Str__Timestamp` (use `_shared/`). |
| **No mocks, no patches** | use the `_Fake_*` pattern from existing tests (e.g. `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/test_Route53__AWS__Client.py`). Subclass + canned data + seam override. |
| **Lab__Experiment shape per delta B.2** | abstract base has: `runner : Lab__Runner` field (injected via `setup(...)`, NOT a parameter to `execute()`); `setup(...) -> 'Self'`; `execute() -> Schema__Lab__Run__Result` (NO `runner` argument); `metadata() -> Schema__Lab__Experiment__Metadata`. |
| **File names match class names** | `Lab__Runner.py` contains class `Lab__Runner`. No `lab_runner.py`. No `E01__zone_inventory.py` either (that's experiments, not your slice). |
| **Lab__Source__Adapter registration is LAZY** | per `02 §0` of the foundation brief — `register_all(source_registry)` is called from `Cli__Lab.py`'s top-level `callback()`, NOT at module import. An operator running `sg aws dns zones list` must pay zero import-time cost for lab's source registrations. |

---

## Scope summary — what to build (one-screen recap)

Full detail in `02__common-foundation.md`. Quick reference:

### Production code under `sgraph_ai_service_playwright__cli/aws/lab/`

```
aws/lab/
├── __init__.py                                       (empty)
├── cli/
│   ├── __init__.py                                   (empty)
│   └── Cli__Lab.py                                   FULL verb tree:
│                                                       list, show, run,
│                                                       runs {list, show, diff},
│                                                       sweep,
│                                                       account {show, set-expected},
│                                                       ledger {show, replay},
│                                                       serve
│                                                     run/show/runs/serve are STUBBED
│                                                     (return "not-implemented" cleanly)
│                                                     in this PR; agents A–E fill them.
├── service/
│   ├── __init__.py                                   (empty)
│   ├── Lab__Runner.py                                full impl
│   ├── Lab__Ledger.py                                full impl (append-only JSONL + file lock)
│   ├── Lab__Sweeper.py                               full impl + R53 scanner; CF/Lambda/etc scanners stubbed
│   ├── Lab__Tagger.py                                thin extension of _shared/Aws__Tagger
│   ├── Lab__Safety__Account_Guard.py                 full impl
│   ├── Lab__Timing.py                                full impl
│   ├── Lab__Phase__Not_Ready__Error.py               exception class (one-liner)
│   ├── Lab__Source__Adapter.py                       skeleton — implements Source__Contract;
│                                                     register_all() is callable but the
│                                                     registry is empty (agents A/D add
│                                                     registrations later).
│   ├── teardown/
│   │   ├── __init__.py                               (empty)
│   │   ├── Lab__Teardown__Dispatcher.py              full impl — maps Enum__Lab__Resource_Type
│   │                                                 → teardown fn
│   │   ├── Lab__Teardown__R53.py                     full impl (uses existing
│   │                                                 Route53__AWS__Client.delete_record /
│   │                                                 batch_delete_records)
│   │   ├── Lab__Teardown__CF.py                      STUB (raises NotImplementedError)
│   │   ├── Lab__Teardown__Lambda.py                  STUB
│   │   ├── Lab__Teardown__ACM.py                     STUB
│   │   ├── Lab__Teardown__EC2.py                     STUB
│   │   ├── Lab__Teardown__SSM.py                     STUB
│   │   └── Lab__Teardown__IAM.py                     STUB
│   ├── experiments/
│   │   ├── __init__.py                               (empty)
│   │   ├── Lab__Experiment.py                        abstract base (per delta B.2 shape)
│   │   ├── registry.py                               module-level dict + helpers
│   │                                                 (get_experiment, list_experiments).
│   │                                                 STARTS EMPTY — agents add entries.
│   │   ├── dns/__init__.py                           (empty — Agent A fills)
│   │   ├── cf/__init__.py                            (empty — Agent C fills)
│   │   ├── lambda_/__init__.py                       (empty — Agent B fills)
│   │   └── transition/__init__.py                    (empty — Agent D fills)
│   └── renderers/
│       ├── __init__.py                               (empty)
│       ├── Render__Table.py                          full impl (Rich-based, generic
│                                                     Schema__Lab__Run__Result renderer)
│       ├── Render__JSON.py                           full impl (pretty JSON)
│       ├── Render__Timeline__ASCII.py                STUB — signature present,
│                                                     body raises NotImplementedError
│                                                     (Agent A fills render_event_list,
│                                                     Agent D adds render_waterfall)
│       └── Render__Histogram__ASCII.py               STUB — signature present
│                                                     (Agent B fills render_durations_ms)
├── schemas/                                          per-class files:
│   ├── __init__.py                                   (empty)
│   ├── Schema__Lab__Ledger__Entry.py
│   ├── Schema__Lab__Run__Result.py
│   ├── Schema__Lab__Experiment__Metadata.py
│   ├── Schema__Lab__Timing__Sample.py
│   ├── Schema__Lab__Sweep__Report.py
│   └── Schema__Lab__Account__Identity.py
├── enums/                                            per-class files:
│   ├── __init__.py                                   (empty)
│   ├── Enum__Lab__Resource_Type.py                   R53_RECORD | CF_DISTRIBUTION | LAMBDA |
│   │                                                 LAMBDA_URL | ACM_CERT | EC2_INSTANCE |
│   │                                                 SG | IAM_ROLE | SSM_PARAM | S3_BUCKET.
│   │                                                 Each value carries teardown_order int.
│   ├── Enum__Lab__Entry__State.py                    PENDING | DELETED | FAILED |
│   │                                                 ABANDONED | DELETED_PENDING_CF_DISABLE
│   └── Enum__Lab__Experiment__Status.py              PENDING | RUNNING | OK | FAILED |
│                                                     TIMEOUT | ABORTED
├── primitives/                                       per-class files:
│   ├── __init__.py                                   (empty)
│   ├── Safe_Str__Lab__Run_Id.py                      pattern <iso-ts-z>__<6-char nonce>
│   ├── Safe_Str__Lab__Entry_Id.py                    uuid4 hex
│   ├── Safe_Str__Lab__Experiment_Name.py             e.g. "propagation-timeline"
│   └── Safe_Int__Duration_Ms.py
└── collections/                                      per-class files:
    ├── __init__.py                                   (empty)
    ├── List__Schema__Lab__Ledger__Entry.py
    └── List__Schema__Lab__Timing__Sample.py
```

### Modifications outside `aws/lab/`

Limited and purely additive:

```
sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py
    + from sgraph_ai_service_playwright__cli.aws.lab.cli.Cli__Lab import lab_app
    + app.add_typer(lab_app, name='lab')

.gitignore
    + .sg-lab/

library/catalogue/cli.md
    add a "sg aws lab" entry to the appropriate section (the file uses
    a stable-filename / fractal-shard layout — add to the table of
    AWS surfaces). Mark status as ✅ FOUNDATION-LANDED, with note
    "experiment slices A–E pending".

library/catalogue/infra.md
    add a brief note about lab tag-driven sweep + the sg:lab:*
    tagging convention (one paragraph).

team/roles/librarian/reality/cli/index.md
    add a line for sg aws lab pointing to a new
    team/roles/librarian/reality/cli/aws-lab.md page.

team/roles/librarian/reality/cli/aws-lab.md   (NEW FILE)
    short reality-doc page describing what FOUNDATION delivers,
    plus a "PROPOSED — does not exist yet" subsection listing
    the experiments still to come (per agents A–E).
```

### Test code under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/`

```
tests/unit/sgraph_ai_service_playwright__cli/aws/lab/
├── __init__.py
├── service/
│   ├── __init__.py
│   ├── test_Lab__Ledger.py                           write/read/replay round-trip;
│   │                                                 partial-write recovery;
│   │                                                 concurrent-writer file-lock test
│   ├── test_Lab__Tagger.py                           every taggable resource type
│   │                                                 gets all 5 sg:lab:* tags + the
│   │                                                 5 canonical _shared/Aws__Tagger
│   │                                                 sg:* tags. Total = 10 tags per
│   │                                                 resource.
│   ├── test_Lab__Safety__Account_Guard.py            in-memory STS, matches and
│   │                                                 mismatches; env-var unset → no-op;
│   │                                                 env-var set + mismatch → raises
│   ├── test_Lab__Sweeper.py                          in-memory R53 client returning a
│   │                                                 mix of tagged + untagged records;
│   │                                                 asserts only resources with ALL 3
│   │                                                 required tags (sg:lab, sg:lab:run-id,
│   │                                                 sg:lab:expires-at) are deleted
│   ├── test_Lab__Runner__In_Memory.py                runs a no-op experiment end-to-end;
│   │                                                 asserts ledger lifecycle
│   │                                                 (start → execute → teardown);
│   │                                                 verifies create_and_register writes
│   │                                                 ledger entry BEFORE invoking factory
│   ├── test_Lab__Source__Adapter.py                  registration is LAZY (not called at
│   │                                                 import); registry empty at foundation
│   │                                                 stage (no experiments yet); calling
│   │                                                 register_all() with an empty registry
│   │                                                 returns 0 sources
│   ├── teardown/
│   │   ├── __init__.py
│   │   └── test_Lab__Teardown__R53.py               in-memory R53 client; verifies
│   │                                                idempotency (re-read before delete)
│   └── test_Lab__Phase__Not_Ready__Error.py         minimal: subclass of Exception,
│                                                    message format
└── cli/
    ├── __init__.py
    └── test_Cli__Lab.py                              Typer smoke tests:
                                                       sg aws lab --help shows all verbs
                                                       sg aws lab list returns empty list
                                                       sg aws lab show <id> returns clean error
                                                       sg aws lab run <nonexistent> errors
                                                       sg aws lab sweep returns "no resources"
                                                       sg aws lab account show prints identity
                                                       sg aws lab serve errors with
                                                         "not implemented in foundation"
                                                       sg aws lab runs diff errors with
                                                         "not implemented in foundation"
```

Pattern for `_Fake_*` doubles: copy the shape from
`tests/unit/sgraph_ai_service_playwright__cli/aws/dns/test_Route53__AWS__Client.py`
(`_Fake_Route53__AWS__Client` + `_Fake_Route53_Boto3_Client`).

For STS, copy from
`tests/unit/sgraph_ai_service_playwright__cli/credentials/service/test_Sg__Aws__Session.py`
or similar.

---

## Acceptance criteria

Run from a fresh checkout of `claude/aws-primitives-support-NVyEh` after your PR is applied:

```bash
# 1. CLI surface
sg aws lab --help                                                              # shows full verb tree
sg aws lab list                                                                # → "no experiments registered yet (P0 ships in agent-A PR)"
sg aws lab account show                                                        # → STS caller identity + region
sg aws lab sweep                                                               # → "no leaked resources"
sg aws lab sweep --apply --older-than 1h                                       # → "no leaked resources"
sg aws lab serve                                                               # → clean error "not implemented in foundation"
sg aws lab runs list                                                           # → "no runs found"
sg aws lab runs diff a b                                                       # → clean error "not implemented in foundation"

# 2. Mutation gate
sg aws lab run dummy                                                           # → clean error "experiment 'dummy' not registered" (gate not reached)
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run dummy                            # → same error (registry still empty)

# 3. Tests
poetry run pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/ -v     # all green

# 4. No regression in existing aws/* tests
poetry run pytest tests/unit/sgraph_ai_service_playwright__cli/aws/ -v         # all green (no regression)

# 5. Sanity — no boto3 import in aws/lab/
grep -rn "^import boto3\|^from boto3" sgraph_ai_service_playwright__cli/aws/lab/   # → empty

# 6. Sanity — no Set__Str / Dict__Str__Str / Dict__Str__Int in aws/lab/
grep -rnE "Set__Str|Dict__Str__Str|Dict__Str__Int" sgraph_ai_service_playwright__cli/aws/lab/    # → empty

# 7. Sanity — _shared/ reuse, not duplication
grep -rn "Enum__Lab__Tier\|Enum__Lab__Tag__Key\|Safe_Str__Lab__Resource_Id\|Safe_Str__Timestamp" sgraph_ai_service_playwright__cli/aws/lab/   # → empty
```

All seven must pass for the PR to ship.

---

## Commit + PR guidance

**Branch:** keep working on `claude/aws-primitives-support-NVyEh` — do NOT branch from here. The pack PR (rev 1 → rev 2 → rev 3) lives on this branch. Add your Foundation implementation commits on top.

**Commit style** — match the repo's existing style (`git log --oneline | head -20` shows the pattern):

- One commit per logical chunk. Suggested sequence:
  1. `feat(v0.3.0): lab foundation — primitives + enums + schemas + collections`
  2. `feat(v0.3.0): lab foundation — _shared/ reuse (Lab__Tagger, ledger, sweeper scaffold)`
  3. `feat(v0.3.0): lab foundation — Lab__Runner + create_and_register + safety net`
  4. `feat(v0.3.0): lab foundation — Lab__Teardown dispatcher + R53 teardown impl + 6 stubs`
  5. `feat(v0.3.0): lab foundation — Lab__Source__Adapter (lazy registration)`
  6. `feat(v0.3.0): lab foundation — Cli__Lab Typer surface + wire-up + catalogue/reality updates`
  7. `test(v0.3.0): lab foundation — unit tests for ledger / tagger / sweeper / runner / cli`

End each commit message with the standard footer:
```
https://claude.ai/code/session_01At77aLh8p3LytA9W4vATGc
```

**Do NOT open a PR.** Dinis opens PRs manually after Architect (Opus) reviews the commits. Push to the branch, then end your turn with a one-paragraph status update listing commits pushed and acceptance results.

---

## What to do FIRST

1. Read everything in the required-reading list above (files 1–11).
2. Run `ls sgraph_ai_service_playwright__cli/aws/_shared/ -R` to see what's there to reuse.
3. Run `cat sgraph_ai_service_playwright__cli/aws/_shared/Mutation__Gate.py sgraph_ai_service_playwright__cli/aws/_shared/Aws__Confirm.py sgraph_ai_service_playwright__cli/aws/_shared/Aws__Tagger.py` to internalise the canonical shapes.
4. Look at `sgraph_ai_service_playwright__cli/aws/s3/` or `sgraph_ai_service_playwright__cli/aws/ec2/` as a v0.2.29 reference implementation — they're the freshest examples of "Typer-cli + Service + Schemas + Enums + Primitives + Tests" the lab should mirror.
5. Then start with the primitives + enums + schemas + collections (commit 1). These have the simplest tests and unblock everything else.

If anything in the brief is ambiguous, **stop and ask Dinis** via a one-line question — don't guess. The pack files (`README.md`, `01`-`08`) are the source of truth; this prompt is a convenience overlay.

Good luck.

— Architect (Opus 4.7), 2026-05-18
