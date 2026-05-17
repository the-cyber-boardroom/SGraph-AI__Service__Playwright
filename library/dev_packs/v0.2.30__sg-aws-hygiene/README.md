---
title: "v0.2.30 — sg aws hygiene pack (Open-1, Open-2, Open-3 from v0.2.29 close-out)"
file: README.md
author: Architect (Claude — Opus 4.7)
date: 2026-05-17
repo: SGraph-AI__Service__Playwright @ dev (v0.2.29 line → targeting v0.2.30)
status: PROPOSED — for Dev pickup after v0.2.29 merges to dev + version bump lands
parent_review: team/roles/architect/reviews/05/17/v0.2.29__milestone-closeout__review.md
related:
  - library/dev_packs/v0.2.29__sg-aws-primitives-expansion/        # the milestone this cleans up after
  - team/claude/debriefs/2026-05-17__v0.2.29-sg-aws-primitives-expansion.md
feature_branch: claude/aws-hygiene-v0.2.30
size: M — ~700 prod LOC + ~300 test LOC + 5 days net (parallelisable to ~2 calendar days)
priority: NORMAL — no blockers; pays down debt accumulated during the 1-day v0.2.29 sprint
---

# v0.2.30 — `sg aws` hygiene pack

Three cleanup items left open after v0.2.29 shipped. None block the milestone merge; all three pay down debt that will compound if left untouched. The three items are independent — they can be three small PRs in parallel, one per item.

> **PROPOSED — does not exist yet.** Picks up after v0.2.29 (root `version` bumped to `0.2.29`) lands on dev.

---

## TL;DR

| Item | What | Where | Effort |
|------|------|-------|-------:|
| **Open-1** | Refactor 131 `monkeypatch` calls into in-memory composition (CLAUDE.md "no mocks, no patches") | 5 CLI test files in `aws/{ec2,fargate,iam,iam/graph,cloudtrail}/` | ~5 days (1/slice, parallel) |
| **Open-2** | Type 91 raw-`str` schema fields with `Safe_Str__*` + replace 3 JSON-encoded escape hatches with proper collections | 7 surface `schemas/` folders (worst: EC2 with 34) | ~3 days (1/surface, parallel) |
| **Open-3** | Replace `boto3.session.Session().region_name` in 6 clients' `current_region()` with `Aws__Region__Resolver` | 6 service clients in `aws/*/service/` | ~30 minutes |

Parallel critical path is **~1.5 calendar days** if three Sonnet sessions take one item each. Sequential is ~5 days.

---

## Item Open-1 — `monkeypatch` → in-memory composition

### The problem

```
Slice B EC2          : 32 monkeypatch calls   tests/.../aws/ec2/cli/test_Cli__EC2.py
Slice C Fargate      : 45 monkeypatch calls   tests/.../aws/fargate/cli/test_Cli__Fargate.py
Slice D IAM graph    : 20 monkeypatch calls   tests/.../aws/iam/graph/cli/test_Cli__Iam__Graph.py
Slice F CloudTrail   : 22 monkeypatch calls   tests/.../aws/cloudtrail/cli/test_Cli__CloudTrail.py
Existing IAM         : 12 monkeypatch calls   tests/.../aws/iam/cli/test_Cli__Iam.py
                       ────
                       131 total
```

CLAUDE.md is explicit: **"No mocks. No patches."** (Testing rule #1). The 5 v0.2.29 test files using `monkeypatch` were all built on the pattern in the pre-v0.2.29 `aws/iam/cli/test_Cli__Iam.py` (which itself violated the rule). Slices A, E, G, H — built later in the milestone — show the canonical pattern.

### The canonical pattern (already in the repo)

Slice A's `S3__AWS__Client__In_Memory` — subclasses the real client, overrides the single boto3 seam:

```python
# tests/unit/sgraph_ai_service_playwright__cli/aws/s3/service/S3__AWS__Client__In_Memory.py

from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client import S3__AWS__Client

class _Fake_S3_Client:
    """Minimal boto3-alike S3 client backed by in-memory stores."""
    def __init__(self, object_store: dict, bucket_store: dict):
        self._objects = object_store
        self._buckets = bucket_store

    def list_buckets(self):
        return {'Buckets': [{'Name': n, 'CreationDate': '...'} for n in self._buckets]}
    # ... etc

class S3__AWS__Client__In_Memory(S3__AWS__Client):
    object_store : dict = None
    bucket_store : dict = None

    def setup(self):
        if self.object_store is None: self.object_store = {}
        if self.bucket_store is None: self.bucket_store = {}
        return self

    def client(self, region: str = None):                                     # override the single boto3 seam
        return _Fake_S3_Client(self.object_store, self.bucket_store)
```

CLI tests then compose the In_Memory client directly — no `monkeypatch.setattr` anywhere:

```python
def test_bucket_list(tmp_path):
    in_memory = S3__AWS__Client__In_Memory()
    in_memory.bucket_store['test-bucket'] = {'Region': 'eu-west-2', 'Created': '...'}
    # CLI verb consults the client via constructor injection or context — no module-level helpers
    ...
```

### The `monkeypatch` shape that needs to go

```python
# the bad pattern — couples tests to internal module structure
def test_cluster_list(monkeypatch, tmp_path):
    monkeypatch.setattr(
        'sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._default_client',
        lambda: Fargate__AWS__Client__In_Memory(...))
    result = runner.invoke(app, ['cluster-list'])
```

When the CLI is reorganised (which it will be — v0.2.30 hygiene), the `_default_client` import path moves, every monkeypatch breaks in confusing ways, and the test author has to re-derive each one.

### Scope (5 PRs, one per slice — they can fire in parallel)

| PR | File | monkeypatch calls | Approach |
|----|------|------------------:|----------|
| Open-1-ec2       | `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/cli/test_Cli__EC2.py` | 32 | Replace `monkeypatch.setattr('...Cli__EC2._default_client', lambda: EC2__AWS__Client__In_Memory(...))` with constructor injection through a Typer `@app.callback` context object holding the In_Memory client; CLI verbs read `ctx.obj['ec2_client']`. |
| Open-1-fargate   | `tests/unit/sgraph_ai_service_playwright__cli/aws/fargate/cli/test_Cli__Fargate.py` | 45 | Same pattern |
| Open-1-iam-graph | `tests/unit/sgraph_ai_service_playwright__cli/aws/iam/graph/cli/test_Cli__Iam__Graph.py` | 20 | Same — Slice D's `_default_writer` + `_default_orchestrator` go via context |
| Open-1-cloudtrail| `tests/unit/sgraph_ai_service_playwright__cli/aws/cloudtrail/cli/test_Cli__CloudTrail.py` | 22 | Same |
| Open-1-iam-legacy| `tests/unit/sgraph_ai_service_playwright__cli/aws/iam/cli/test_Cli__Iam.py` | 12 | Same — predates v0.2.29 but is the root the others copied; clean it up too |

Per-PR pattern (same shape for all 5):

**Source CLI module change:**

```python
# was:
def _default_client():
    return Fargate__AWS__Client()

def cluster_list(...):
    client = _default_client()
    ...

# becomes:
@app.callback()
def _setup(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {'fargate_client': Fargate__AWS__Client().setup()}

def cluster_list(ctx: typer.Context, ...):
    client = ctx.obj['fargate_client']
    ...
```

**Test change:**

```python
# was:
def test_cluster_list(monkeypatch):
    monkeypatch.setattr('...Cli__Fargate._default_client',
                        lambda: Fargate__AWS__Client__In_Memory())
    runner.invoke(app, ['cluster-list'])

# becomes:
def test_cluster_list():
    in_memory = Fargate__AWS__Client__In_Memory().setup()
    in_memory.create_cluster('test')
    runner.invoke(app, ['cluster-list'], obj={'fargate_client': in_memory})
```

### Acceptance

```bash
# Per slice — same shape for all 5
grep -c monkeypatch tests/unit/sgraph_ai_service_playwright__cli/aws/<surface>/cli/test_Cli__<Surface>.py
# → 0

pytest tests/unit/sgraph_ai_service_playwright__cli/aws/<surface>/ -v
# → all tests still pass (no count regression)

# Repo-wide check
grep -rln monkeypatch tests/unit/sgraph_ai_service_playwright__cli/aws/
# → empty
```

### Estimated effort

~1 day per slice, parallelisable. Each PR is small (one CLI module + one test file). 5 days sequential, ~1 day parallel.

---

## Item Open-2 — Raw-`str` schema fields → `Safe_Str__*`

### The problem

91 raw-`str` fields across 7 surfaces. CLAUDE.md rule #2: **"Zero raw primitives — no `str`, `int`, `float`, `list`, `dict` as attributes."**

| Surface | Raw-`str` fields | Notes |
|---------|---------------:|-------|
| `bedrock` | **0** | Reference — properly types every field |
| `observe` | 2 | Small, defensible |
| `s3` | 11 | M-3 from prior review |
| `fargate` | 13 | |
| `cloudtrail` | 14 | |
| `creds` | 17 | Security-sensitive surface — types should land before AppSec review pass |
| `ec2` | 34 | Worst; includes M-5 JSON-encoded escape hatches |

EC2 breakdown (the worst surface):

| File | Raw-`str` fields | Notes |
|------|---:|---|
| `Schema__EC2__Create__Request.py` | 6 | name, key_pair, subnet_id, security_groups, user_data + 1 |
| `Schema__EC2__Instance.py` | 6 | name, public_ip, private_ip, launch_time, key_name + 1 |
| `Schema__EC2__Instance__Detail.py` | **17** | **Includes the JSON-encoded escape hatches: `tags_raw`, `security_groups_raw`, `block_devices_raw` — these need proper `Dict__*` / `List__*` collections, not just `Safe_Str__*` wrapping** |
| `Schema__EC2__Pricing.py` | 5 | region, price_per_hour, price_per_second, currency, os |

### The right pattern (Bedrock proves it)

```python
# Bedrock — zero raw-str. Reference for the others.
class Schema__Bedrock__Model(Type_Safe):
    model_id          : Safe_Str__Bedrock__Model_Id
    model_name        : Safe_Str__Bedrock__Model_Name
    provider          : Enum__Bedrock__Provider
    provider_name     : Safe_Str__Bedrock__Provider_Name
    input_modalities  : List__Safe_Str__Bedrock__Modality
    output_modalities : List__Safe_Str__Bedrock__Modality
    region            : Safe_Str__AWS__Region
```

### Special case: M-5 JSON-encoded escape hatches in EC2

```python
# the wrong shape — abandoning Type_Safe at the boundary
class Schema__EC2__Instance__Detail(Type_Safe):
    tags_raw             : str  = ''    # json.dumps(tags) — CLI then json.loads to render
    security_groups_raw  : str  = ''    # json.dumps(SGs)
    block_devices_raw    : str  = ''    # json.dumps(BDMs)
```

The fix is **not** a `Safe_Str__*` wrapper around JSON strings. It's the actual typed shape:

```python
# create the missing schemas + collections first
class Schema__EC2__Security_Group__Ref(Type_Safe):
    group_id   : Safe_Str__EC2__SG_Id
    group_name : Safe_Str__AWS__Tag_Value

class List__Schema__EC2__Security_Group__Ref(Type_Safe__List):
    expected_type = Schema__EC2__Security_Group__Ref

class Dict__EC2__Tag(Type_Safe__Dict):
    expected_key_type   = Safe_Str__AWS__Tag_Key
    expected_value_type = Safe_Str__AWS__Tag_Value

class Schema__EC2__Block_Device__Mapping(Type_Safe):
    device_name  : Safe_Str__EC2__Device_Name
    volume_id    : Safe_Str__EC2__Volume_Id
    volume_size  : Safe_Int__EC2__GiB
    delete_on_termination : bool

# then re-type the schema
class Schema__EC2__Instance__Detail(Type_Safe):
    tags             : Dict__EC2__Tag
    security_groups  : List__Schema__EC2__Security_Group__Ref
    block_devices    : List__Schema__EC2__Block_Device__Mapping
```

CLI consumers then iterate typed objects instead of `json.loads(detail.tags_raw)`.

### Scope (7 PRs, one per surface — parallelisable)

| PR | Surface | Fields | New primitives needed | Special work |
|----|---------|------:|----------------------|--------------|
| Open-2-ec2 | `aws/ec2/` | 34 | ~8 (Name, Key_Pair, Subnet_Id, SG_Id, Volume_Id, Device_Name, etc.) | + 3 new schemas + 3 collections for M-5 fix |
| Open-2-creds | `aws/creds/` | 17 | ~6 (Scope_Name, Caller_Identity, Audit_Action, etc.) | AppSec-touching surface |
| Open-2-cloudtrail | `aws/cloudtrail/` | 14 | ~5 (Event_Id, Event_Source, Event_Name, User_Identity, Source_IP) | |
| Open-2-fargate | `aws/fargate/` | 13 | ~5 (Cluster_Name, Task_Family, Container_Name, Cpu, Memory) | |
| Open-2-s3 | `aws/s3/` | 11 | ~4 (Key, ETag, Storage_Class, Content_Type) | M-3 from prior review |
| Open-2-observe | `aws/observe/` | 2 | 1 (`Enum__Observe__Source__Status`) | Smallest |
| Open-2-bedrock | n/a | 0 | n/a | Reference; no work |

### Acceptance per surface

```bash
grep -h "^\s*[a-z_]\+\s*:\s*str\s*=" sgraph_ai_service_playwright__cli/aws/<surface>/schemas/*.py | wc -l
# → 0

pytest tests/unit/sgraph_ai_service_playwright__cli/aws/<surface>/ -v
# → all tests pass (some may need updating to use the new primitives)

# Specifically for EC2 — verify the M-5 escape hatches are gone
grep -n "_raw.*:.*str" sgraph_ai_service_playwright__cli/aws/ec2/schemas/Schema__EC2__Instance__Detail.py
# → empty
```

### Estimated effort

~3-4 hours per surface, parallelisable. EC2 is bigger (~half a day) due to the M-5 work. 3 days sequential, ~half a day parallel.

---

## Item Open-3 — `current_region()` → `Aws__Region__Resolver`

### The problem

```python
# Repeated in 6 AWS clients today
def current_region(self) -> str:
    region = boto3.session.Session().region_name
    return region if region else FALLBACK_REGION
```

This reads boto3's region (from `~/.aws/config`, `AWS_DEFAULT_REGION`, or IMDS). It **does not** consult the active sg role's region. Result: the active client call uses the role's region correctly (via `boto3_client_from_context(..., region=...)`), but `current_region()` (used for display, logs, and the Bedrock check output) reports a different region. Subtle inconsistency.

### The fix

```python
from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver

def current_region(self) -> str:
    return str(Aws__Region__Resolver().resolve())
```

`Aws__Region__Resolver` already encodes the right precedence (flag > AWS_REGION > active role > resource hint > SG_AWS__DEFAULT_REGION > us-east-1).

### Scope (single PR — touches 6 files)

```
sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Control__AWS__Client.py
sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Runtime__AWS__Client.py
sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Agent__AWS__Client.py
sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Tool__AWS__Client.py
sgraph_ai_service_playwright__cli/aws/cloudtrail/service/CloudTrail__AWS__Client.py
# + any others with current_region() — grep first
grep -l "def current_region" sgraph_ai_service_playwright__cli/aws/*/service/*.py
```

Delete the top-level `import boto3` from each of these files (the only remaining use was `current_region()` — once removed, the import is dead).

### Acceptance

```bash
grep -rn "boto3.session.Session" sgraph_ai_service_playwright__cli/aws/
# → 0 matches in production code (test fixtures may keep it; that's fine)

pytest tests/unit/sgraph_ai_service_playwright__cli/aws/ -q
# → 689 tests still pass

# Behaviour check
sg credentials switch dev-role-eu-west-2
sg aws bedrock check
# → output shows "region=eu-west-2", not the boto3-default region
```

### Estimated effort

~30 minutes. Single commit.

---

## Sequencing

**All three items are independent.** Three Sonnet sessions can pick one each and fire in parallel.

If only one session is available, the recommended order:

1. **Open-3 first** (30 minutes) — quick win; affects diagnostic output (Bedrock check), so worth getting right early.
2. **Open-2 next** (~3 days) — payback is large (M-3 + M-5 from prior reviews) and unlocks proper typed iteration in CLI verbs.
3. **Open-1 last** (~5 days) — biggest scope; each slice can be a separate PR. Don't bundle them.

---

## Out of scope (other v0.2.30 deferrals, NOT in this pack)

These were called out in the v0.2.29 close-out + locked decisions. **Each warrants its own dev pack** — do NOT roll them into the hygiene pack:

| Deferral | Source | Suggested pack name |
|----------|--------|---------------------|
| Container-hosts primitive (Kubernetes-shaped on EC2) | LD#11; source brief `v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md` | `v0.2.30__sg-compute-container-hosts` (separate; large) |
| Instance-sizing measurement programme | LD#12; source brief `v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md` | `v0.2.30__sg-instance-sizing-experiments` |
| Bedrock kb/guardrail/eval/observe | LD#5 | `v0.2.30__sg-aws-bedrock-extensions` |
| IAM-graph Phase 4 (CloudTrail-evidence) | LD#6 | `v0.2.30__sg-aws-iam-graph-phase-4` |
| Scoped-creds Phase 5 (deployed service) | LD#7 | `v0.3.x__sg-aws-creds-deployed-service` |
| `--apply` mode for `sg aws bedrock setup` | `02__chat-ux-and-setup.md §"Mode B"` | Fold into Bedrock-extensions pack above |

Vault-aware S3 wrappers (LD#10) depend on the Vault Synchronizer Tool which isn't on the roadmap yet.

---

## Commit + PR template

Per item:

```
fix(v0.2.30): Open-<N> — <one-line summary>

Closes Open-<N> from the v0.2.29 close-out architect review at
team/roles/architect/reviews/05/17/v0.2.29__milestone-closeout__review.md

<2-3 line body describing the specific scope>

https://claude.ai/code/session_XXX
```

Each item's PR targets `dev` directly (no integration branch needed — they're independent). Open-1 has 5 sub-PRs that can land in any order.

---

## What this pack is + isn't

**Is:** Three deferred-cleanup items from v0.2.29's close-out review. No new features. No new verbs. No new schemas (except the typed M-5 replacements in EC2). No new dependencies.

**Isn't:** Not a new milestone. Not a refactor of `aws/_shared/`. Not addressing the larger v0.2.30 deferrals (container hosts, instance sizing, Bedrock extensions, IAM graph Phase 4) — those are separate packs.

---

## Pointer back

- Parent review (Open-1/2/3 originate here): [`team/roles/architect/reviews/05/17/v0.2.29__milestone-closeout__review.md`](../../../team/roles/architect/reviews/05/17/v0.2.29__milestone-closeout__review.md)
- Original Slice B review (M-3 + M-5): [`team/roles/architect/reviews/05/17/v0.2.29__slice-b-ec2__review.md`](../../../team/roles/architect/reviews/05/17/v0.2.29__slice-b-ec2__review.md)
- v0.2.29 debrief: [`team/claude/debriefs/2026-05-17__v0.2.29-sg-aws-primitives-expansion.md`](../../../team/claude/debriefs/2026-05-17__v0.2.29-sg-aws-primitives-expansion.md)
- Canonical In-memory pattern reference: `tests/unit/sgraph_ai_service_playwright__cli/aws/s3/service/S3__AWS__Client__In_Memory.py`
- Canonical typed-schema reference (Bedrock — 0 raw-str): `sgraph_ai_service_playwright__cli/aws/bedrock/schemas/`
- Foundation helpers used: `aws/_shared/Aws__Region__Resolver.py` (Open-3), `aws/_shared/Aws__Confirm.py` (already done in v0.2.29)
