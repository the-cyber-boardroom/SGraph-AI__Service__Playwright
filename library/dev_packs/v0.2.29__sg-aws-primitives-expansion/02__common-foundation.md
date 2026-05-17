---
title: "02 — Common foundation (Agent 0 — must land first)"
file: 02__common-foundation.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
size: S (small) — ~1500 prod lines, ~600 test lines, ~1 day
delivers: shared scaffold that every sibling pack depends on
---

# 02 — Common foundation (Agent 0)

**Everything in this file must land in a single PR before any sibling pack starts.** Without it, the per-slice work has no harness to plug into.

Owner: a single dedicated "Foundation" PR — Sonnet, Opus-reviewed. Size: ~1 day, ~1500 prod lines + ~600 test lines.

---

## 1. Scope of the Foundation PR

Production code lands across three locations:

### 1.1 New shared module — `sgraph_ai_service_playwright__cli/aws/_shared/`

The cross-surface scaffolding. New folder; existing surfaces are NOT migrated to it in this PR (separate cleanup later).

```
aws/_shared/
├── __init__.py                          # empty
├── Mutation__Gate.py                    # @require_mutation_gate decorator
├── Aws__Tagger.py                       # canonical sg:* tag application
├── Aws__Region__Resolver.py             # region precedence resolver
├── Aws__Confirm.py                      # [y/N] prompt + --yes / --dry-run helpers
├── schemas/
│   ├── Schema__AWS__Tag.py              # {key, value}
│   ├── Schema__AWS__ARN.py              # parsed ARN
│   ├── Schema__AWS__Resource__Reference.py
│   └── Schema__AWS__Source__Event.py    # one row from any observability source
├── primitives/
│   ├── Safe_Str__AWS__ARN.py
│   ├── Safe_Str__AWS__Region.py
│   ├── Safe_Str__AWS__Account_Id.py
│   ├── Safe_Str__AWS__Tag_Key.py
│   └── Safe_Str__AWS__Tag_Value.py
├── enums/
│   ├── Enum__AWS__Surface.py            # S3 | EC2 | FARGATE | BEDROCK | CLOUDTRAIL | CREDS | OBSERVE | IAM_GRAPH
│   └── Enum__AWS__Mutation__Tier.py     # READ_ONLY | MUTATING_LOW | MUTATING_HIGH
├── collections/
│   ├── List__Schema__AWS__Tag.py
│   └── List__Schema__AWS__Source__Event.py
└── source_contract/
    ├── __init__.py
    ├── Source__Contract.py              # ABC: connect / list / tail / query / stats / schema
    ├── Source__Query.py                 # request shape
    ├── Source__Result__Page.py          # paged result wrapper
    └── Source__Stream.py                # streaming iterator wrapper
```

### 1.2 New surface stubs — one folder per slice

Foundation creates the empty surface folder for each new Click group so sibling packs only add verbs and bodies — no top-level shape conflicts.

| Folder | Foundation ships | Sibling pack fills in |
|--------|------------------|------------------------|
| `aws/s3/` | `cli/Cli__S3.py` skeleton with locked verb names; `service/S3__AWS__Client.py` interface stub; per-class schema/enum/primitive stubs raising `NotImplementedError` | Slice A |
| `aws/ec2/` | same shape | Slice B |
| `aws/fargate/` | same shape | Slice C |
| `aws/iam/graph/` | sub-group registration only (existing `aws/iam/` package gains a `graph/` subfolder); `Cli__Iam__Graph.py` skeleton | Slice D |
| `aws/bedrock/` | same shape; three sub-groups (`chat`, `agent`, `tool`) wired | Slice E |
| `aws/cloudtrail/` | same shape; `CloudTrail__AWS__Client` interface stub (consumed by Slice H) | Slice F |
| `aws/creds/` | same shape | Slice G |
| `aws/observability/` | same shape; `Cli__Observe.py` skeleton with REPL entry-point stub | Slice H |

For each, Foundation ships **interface signatures only** — every method body raises `NotImplementedError("agent-X owns this")`. The sibling packs fill in the bodies and never edit the signatures (signature changes would mean re-coordinating across slices).

### 1.3 Top-level Click wiring — `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py`

Adds seven new `add_typer` (or `add_command`) lines to the top-level `sg aws` group:

```python
# (existing lines — acm, billing, cf, dns, iam, lambda_, logs, credentials)
app.add_typer(Cli__S3.app,         name='s3')
app.add_typer(Cli__EC2.app,        name='ec2')
app.add_typer(Cli__Fargate.app,    name='fargate')
app.add_typer(Cli__Bedrock.app,    name='bedrock')
app.add_typer(Cli__CloudTrail.app, name='cloudtrail')
app.add_typer(Cli__Creds.app,      name='creds')
app.add_typer(Cli__Observe.app,    name='observe')
```

Plus the `iam graph` sub-group wired to the existing `iam` Typer app.

This is the **only file all eight sibling slices indirectly touch**, and only Foundation edits it. After Foundation merges, sibling packs add verbs *inside* their own surface — not at the top level.

### 1.4 Test scaffolding — `tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/`

Per-class tests for every Foundation file. Plus:

- `Test__Aws__Session__Factory.py` — composes an `Sg__Aws__Session` for in-memory tests (no mocks, no patches; uses moto-style in-memory backends already provided by `osbot-aws`, gated by env var when the backend isn't available)
- `Test__Mutation__Gate.py` — verifies the decorator behaves identically for every surface name

### 1.5 Documentation deltas

- `library/docs/cli/sg-aws/01__getting-started.md` gets a new row in the mutation-gate table for every new env var (Foundation edits this — sibling packs do not).
- `library/docs/cli/sg-aws/README.md` "at-a-glance command map" gets seven new tree branches added.
- `library/docs/cli/sg-aws/08__credentials.md` is created (covers the existing v0.2.28 `sg aws credentials` verbs — a small backfill the Foundation PR delivers because no sibling owns it).

The eight new per-surface user-guide pages (`09__s3.md` ... `16__observe.md`) are owned by their respective sibling packs.

### 1.6 Reality-doc delta

- `team/roles/librarian/reality/aws-and-infrastructure/index.md` gains the eight PROPOSED surfaces with the `PROPOSED — does not exist yet` marker. Each sibling pack updates the marker to `LANDED — v0.2.29` in its own PR when its slice lands.

---

## 2. The locked public API

These signatures are the contract sibling packs build against. Foundation locks them; sibling packs add bodies but never change shapes.

### 2.1 `Mutation__Gate.require_mutation_gate(env_var: str)`

Decorator. Reads `os.environ.get(env_var)`. If unset or != `'1'`, raises `Mutation_Gate__Not_Set(env_var)`. The exception is caught at the Typer error boundary and rendered as a Rich panel matching the existing convention (see `aws/dns/cli/`).

### 2.2 `Aws__Tagger.tags_for(surface: Enum__AWS__Surface, verb: str) -> List__Schema__AWS__Tag`

Returns the five-tag set described in `01__scope-and-architecture.md §3.6`. Every `create_*` call in every surface passes the result through.

### 2.3 `Aws__Region__Resolver.resolve(region_flag: Optional[Safe_Str__AWS__Region], resource_hint: Optional[Safe_Str__AWS__Region]) -> Safe_Str__AWS__Region`

Applies the precedence in `01 §3.7`.

### 2.4 `Aws__Confirm.confirm_or_abort(message: str, yes: bool, dry_run: bool) -> bool`

Returns `True` if execution should proceed. Handles the `--yes` shortcut and the `--dry-run` skip uniformly.

### 2.5 `Source__Contract` (ABC)

Six methods every observability source implements:

```python
class Source__Contract(Type_Safe, ABC):
    @abstractmethod
    def connect(self) -> bool: ...
    @abstractmethod
    def list_streams(self) -> List__Schema__Source__Stream__Ref: ...
    @abstractmethod
    def tail(self, stream: Safe_Str, since: Safe_Str__Timestamp) -> Source__Stream: ...
    @abstractmethod
    def query(self, q: Source__Query) -> Source__Result__Page: ...
    @abstractmethod
    def stats(self, stream: Safe_Str, agg: Enum__Source__Aggregation) -> Schema__Source__Stats: ...
    @abstractmethod
    def schema(self, stream: Safe_Str) -> Schema__Source__Stream__Schema: ...
```

Slice A, F, and H all build against this. The existing `aws/logs/` (CloudWatch) source is **not** migrated to this contract in Foundation — Slice H wraps it via an adapter.

---

## 3. What Foundation does NOT do

- Does NOT implement any verb body. Every body raises `NotImplementedError`.
- Does NOT migrate existing surfaces (`acm`, `billing`, `cf`, `dns`, `iam`, `lambda`) to `aws/_shared/`. That's a separate hygiene PR after v0.2.29 ships.
- Does NOT write the user-guide pages for the new surfaces (sibling packs own those).
- Does NOT update reality-doc per-surface entries (sibling packs own those).

---

## 4. Acceptance for the Foundation PR

```bash
# 1. Type-check / lint pass clean
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/ -v

# 2. Top-level sg aws --help shows the eight new groups
sg aws --help                                                       # → s3, ec2, fargate, bedrock, cloudtrail, creds, observe visible
sg aws iam --help                                                   # → graph sub-group visible
sg aws s3 --help                                                    # → verb tree visible (every verb raises NotImplementedError with a clear message)
sg aws bedrock --help                                               # → chat / agent / tool sub-groups visible

# 3. Mutation gate works
sg aws s3 rm s3://test/foo                                          # → "SG_AWS__S3__ALLOW_MUTATIONS must be set" Rich panel
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 rm s3://test/foo --yes      # → NotImplementedError (body not yet filled in) — but the gate let it through

# 4. Tagger / region resolver round-trip via in-memory tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/Test__Aws__Tagger.py -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/Test__Aws__Region__Resolver.py -v

# 5. User-guide additions present
ls library/docs/cli/sg-aws/08__credentials.md                       # exists
grep 'SG_AWS__S3__ALLOW_MUTATIONS' library/docs/cli/sg-aws/01__getting-started.md  # → table row exists
```

---

## 5. Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-foundation` (off `claude/aws-primitives-support-uNnZY`)

Commit messages follow the repo style: `feat(v0.2.29): foundation — shared aws scaffold + 8 surface stubs`.

Open PR against `claude/aws-primitives-support-uNnZY` (integration branch). Tag the Opus coordinator and request Architect review before merge. Once merged, the Opus coordinator unblocks all eight sibling slices in parallel.
