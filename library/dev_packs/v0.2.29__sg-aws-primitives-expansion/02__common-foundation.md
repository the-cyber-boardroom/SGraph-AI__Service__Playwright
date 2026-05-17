---
title: "02 — Common foundation (Agent 0 — must land first)"
file: 02__common-foundation.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
size: S-M — ~1700 prod lines, ~700 test lines, ~1.5 days (grew slightly to absorb the credentials remount + primitive de-duplication called out in the 2026-05-17 architect review)
delivers: shared scaffold that every sibling pack depends on, plus two one-time consolidations
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
├── primitives/                          # canonical home — supersedes duplicates listed below
│   ├── Safe_Str__AWS__ARN.py
│   ├── Safe_Str__AWS__Region.py         # consolidates 3 existing copies
│   ├── Safe_Str__AWS__Account_Id.py     # consolidates `ec2/primitives/` + `credentials/primitives/` copies (added 2026-05-17)
│   ├── Safe_Str__AWS__Role__ARN.py      # consolidates `credentials/primitives/` copy
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
| `aws/observe/` | same shape; `Cli__Observe.py` skeleton with REPL entry-point stub. Folder is `observe` (not `observability`) to avoid clash with existing `__cli/observability/` (different semantics — see Slice H README) | Slice H |

For each, Foundation ships **interface signatures only** — every method body raises `NotImplementedError("agent-X owns this")`. The sibling packs fill in the bodies and never edit the signatures (signature changes would mean re-coordinating across slices).

### 1.3 Top-level Click wiring — two files

**`sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py`** — adds eight new `add_typer` lines (seven new namespaces + the credentials remount per locked decision #13):

```python
# (existing lines — acm, billing, cf, dns, iam, lambda_, logs)
from sgraph_ai_service_playwright__cli.credentials.cli.Cli__Credentials import app as _credentials_app

app.add_typer(_credentials_app,    name='credentials')  # remount of existing sg credentials (locked decision #13)
app.add_typer(Cli__S3.app,         name='s3')
app.add_typer(Cli__EC2.app,        name='ec2')
app.add_typer(Cli__Fargate.app,    name='fargate')
app.add_typer(Cli__Bedrock.app,    name='bedrock')
app.add_typer(Cli__CloudTrail.app, name='cloudtrail')
app.add_typer(Cli__Creds.app,      name='creds')
app.add_typer(Cli__Observe.app,    name='observe')
```

**`sg_compute/cli/Cli__SG.py`** — convert the existing `sg credentials` mount into a hidden alias (so `sg credentials …` keeps working for muscle memory and existing scripts, but `sg --help` shows only `sg aws credentials`):

```python
# was: app.add_typer(_credentials_app, name='credentials', help='…')
app.add_typer(_credentials_app, name='credentials', hidden=True)  # alias of sg aws credentials; drop in v0.2.30
```

Plus the `iam graph` sub-group wired to the existing `iam` Typer app inside `aws/iam/cli/Cli__Iam.py`:

```python
from sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph import graph_app
iam_app.add_typer(graph_app, name='graph')
```

These are the **only files all eight sibling slices indirectly touch**, and only Foundation edits them. After Foundation merges, sibling packs add verbs *inside* their own surface — not at the top level.

### 1.4 Test scaffolding — `tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/`

Per-class tests for every Foundation file. Plus:

- `Test__Aws__Session__Factory.py` — composes an `Sg__Aws__Session` for in-memory tests (no mocks, no patches; uses moto-style in-memory backends already provided by `osbot-aws`, gated by env var when the backend isn't available)
- `Test__Mutation__Gate.py` — verifies the decorator behaves identically for every surface name

### 1.5 Documentation deltas

- `library/docs/cli/sg-aws/01__getting-started.md` gets a new row in the mutation-gate table for every new env var (Foundation edits this — sibling packs do not).
- `library/docs/cli/sg-aws/README.md` "at-a-glance command map" gets seven new tree branches added + the `credentials` row updated to reflect the new `sg aws credentials` path.
- `library/docs/cli/sg-aws/08__credentials.md` already exists in this dev-pack drop and accurately describes the post-remount command surface (`sg aws credentials …`). Foundation only needs to land the remount in `Cli__Aws.py` for the doc to be true.

The eight new per-surface user-guide pages (`09__s3.md` ... `16__observe.md`) are owned by their respective sibling packs.

### 1.6 Reality-doc delta

The reality-doc home is `team/roles/librarian/reality/cli/` (matching existing `cli/aws-dns.md` / `cli/observability.md`), **not** the `aws-and-infrastructure/` domain referenced in earlier drafts (that domain doesn't exist).

Foundation creates **`cli/aws.md`** as the umbrella index for the `sg aws` namespace:

- Lists all currently-mounted `sg aws X` sub-groups
- Names the `_shared/` scaffold (mutation gate, tagger, region resolver, source contract, primitives)
- Lists the eight PROPOSED surfaces with the `PROPOSED — does not exist yet` marker
- Each sibling pack updates its own row to `LANDED — v0.2.29` in its own PR when its slice lands, AND creates its own `cli/aws-<surface>.md` per the architect-review naming convention

Foundation also adds a one-line cross-reference from the existing `cli/observability.md` saying "the AMP/OpenSearch/Grafana infrastructure surface lives here; the unified observability READ surface lives at `cli/aws-observe.md` (Slice H)" so future readers don't get the two confused.

---

## 2. The locked public API

These signatures are the contract sibling packs build against. Foundation locks them; sibling packs add bodies but never change shapes.

### 2.1 `Mutation__Gate.require_mutation_gate(env_var: str)`

Decorator. Reads `os.environ.get(env_var)`. If unset or != `'1'`, raises `Mutation_Gate__Not_Set(env_var)`. The exception is caught at the Typer error boundary and rendered as a Rich panel matching the existing convention (see `aws/dns/cli/`).

### 2.2 `Aws__Tagger.tags_for(surface: Enum__AWS__Surface, verb: str) -> List__Schema__AWS__Tag`

Returns the five-tag set described in `01__scope-and-architecture.md §3.6`. Every `create_*` call in every surface passes the result through.

### 2.3 `Aws__Region__Resolver.resolve(region_flag: Optional[Safe_Str__AWS__Region], resource_hint: Optional[Safe_Str__AWS__Region]) -> Safe_Str__AWS__Region`

Applies the precedence in `01 §3.7`. Importantly: queries `Sg__Aws__Context.get_current_role()` + `Credentials__Store.role_get()` to read the active role's region as one of the precedence tiers — this is what keeps the resolver consistent with `Sg__Aws__Session`'s own region selection.

### 2.6 Named-resource → verb sub-trees use the `Lambda__Click__Group` pattern

Slices that need "select a resource by name, then run a verb on it" (Slice B EC2 `<id-or-name>` resolution, Slice E Bedrock `agent <name>` + `tool * session <id>`, Slice C Fargate `task-describe <task-id>`) **reuse the existing `Lambda__Click__Group` two-level dynamic Click group pattern** at `sgraph_ai_service_playwright__cli/aws/lambda_/cli/Lambda__Click__Group.py`. That pattern already proves out the REPL prefix navigation story (`sg-c info` works because `node.commands.items()` enumerates real Command objects).

Foundation does NOT extract a shared base class — the pattern is small enough to copy. Each slice imports the existing module as a reference and produces its own per-resource group.

### 2.7 Tagging convention — `sg:session-id` added

The five-tag set in `01 §3.6` is the **minimum**. Foundation tagger also writes an optional `sg:session-id` tag when the verb runs inside an `sg aws observe` session capture (Slice H) or when an explicit `--session-id` flag is passed. This is the correlation key Slice H's `agent-trace` uses to join across S3 / CloudWatch / CloudTrail / vault sources.

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
- Does NOT migrate the direct `boto3.client('s3')` calls in `__cli/elastic/lets/cf/*/service/S3__*.py` (4 files) to the new `S3__AWS__Client` — Slice A owns that migration (per architect review §2.4).
- Does NOT write the user-guide pages for the new surfaces (sibling packs own those).
- Does NOT update reality-doc per-surface entries (sibling packs own those).

### 3.1 Why Foundation owns `Source__Contract` (decision recap)

The architect review (§4.1) flagged that `Source__Contract` could ship in Slice H instead of Foundation. We keep it in Foundation because:

- Two slices (A, F) ship adapters for it; landing the contract first prevents an A↔F↔H signature negotiation mid-flight.
- Foundation includes a `Test__Source__Contract__Behaviour.py` adapter contract test that exercises every method on a stub adapter — locks the signatures hard.
- If a sibling slice genuinely needs a signature change, the rule from `03 §6.3` applies: raise Architect-review request, no in-PR amendment.

---

## 4. Acceptance for the Foundation PR

```bash
# 1. Type-check / lint pass clean
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/ -v

# 2. Top-level sg aws --help shows the eight new groups + credentials remount
sg aws --help                                                       # → credentials, s3, ec2, fargate, bedrock, cloudtrail, creds, observe visible
sg aws iam --help                                                   # → graph sub-group visible
sg aws s3 --help                                                    # → verb tree visible (every verb raises NotImplementedError with a clear message)
sg aws bedrock --help                                               # → chat / agent / tool sub-groups visible

# 2b. Credentials remount round-trip
sg aws credentials list                                             # → same output as pre-Foundation `sg credentials list`
sg credentials list                                                 # → still works (hidden alias); not in `sg --help`
sg --help | grep -F credentials                                     # → no match (alias is hidden)

# 3. Mutation gate works
sg aws s3 rm s3://test/foo                                          # → "SG_AWS__S3__ALLOW_MUTATIONS must be set" Rich panel
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 rm s3://test/foo --yes      # → NotImplementedError (body not yet filled in) — but the gate let it through

# 4. Tagger / region resolver round-trip via in-memory tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/Test__Aws__Tagger.py -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/Test__Aws__Region__Resolver.py -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/_shared/Test__Source__Contract__Behaviour.py -v

# 4b. Primitive consolidation kept callers green
pytest tests/unit/sgraph_ai_service_playwright__cli/ec2/ -v          # legacy callers still pass via deprecation re-exports (if used)
pytest tests/unit/sgraph_ai_service_playwright__cli/credentials/ -v  # 146+ tests still pass

# 5. User-guide additions present
ls library/docs/cli/sg-aws/08__credentials.md                       # exists
grep 'SG_AWS__S3__ALLOW_MUTATIONS' library/docs/cli/sg-aws/01__getting-started.md  # → table row exists

# 6. Reality-doc additions present
ls team/roles/librarian/reality/cli/aws.md                          # NEW — sg aws namespace overview
grep 'PROPOSED — does not exist yet' team/roles/librarian/reality/cli/aws.md  # → 8 markers, one per sibling slice
```

---

## 5. Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-foundation` (off `claude/aws-primitives-support-uNnZY`)

Commit messages follow the repo style: `feat(v0.2.29): foundation — shared aws scaffold + 8 surface stubs`.

Open PR against `claude/aws-primitives-support-uNnZY` (integration branch). Tag the Opus coordinator and request Architect review before merge. Once merged, the Opus coordinator unblocks all eight sibling slices in parallel.
