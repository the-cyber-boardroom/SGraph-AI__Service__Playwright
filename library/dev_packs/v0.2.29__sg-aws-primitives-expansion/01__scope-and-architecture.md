---
title: "01 — Scope and architecture"
file: 01__scope-and-architecture.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 01 — Scope and architecture

What the v0.2.29 milestone delivers, what it deliberately does not, and how the new surfaces slot into the existing `aws/` package layout and the reality doc.

---

## 1. What's in

Eight new `sg aws *` Click trees, each backed by a folder under `sgraph_ai_service_playwright__cli/aws/<surface>/` mirroring the established shape (`cli/ / service/ / schemas/ / enums/ / primitives/ / collections/`).

| Surface | Folder | Mutation gate | Read-only verbs | Mutating verbs |
|---------|--------|---------------|-----------------|----------------|
| `s3` | `aws/s3/` | `SG_AWS__S3__ALLOW_MUTATIONS=1` | `ls`, `view`, `cat`, `tail`, `head`, `stat`, `presign`, `search`, `bucket-list`, `bucket-stat` | `edit` (vim round-trip), `cp`, `mv`, `rm`, `sync`, `bucket-create`, `bucket-config` |
| `ec2` | `aws/ec2/` | `SG_AWS__EC2__ALLOW_MUTATIONS=1` | `list`, `describe`, `ssh-info`, `tags` | `create`, `start`, `stop`, `terminate` |
| `fargate` | `aws/fargate/` | `SG_AWS__FARGATE__ALLOW_MUTATIONS=1` | `cluster-list`, `task-list`, `task-describe`, `task-logs`, `task-def list/show` | `cluster-create/delete`, `task-run/stop`, `task-def register` |
| `iam graph` | `aws/iam/graph/` (sub-tree) | `SG_AWS__IAM__ALLOW_MUTATIONS=1` (existing) | `discover`, `show`, `walk`, `filter`, `stats` | `delete` (only on filtered candidate set; dry-run default) |
| `bedrock` | `aws/bedrock/` | `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1` (agent/tool only — `chat` is read-only) | `chat {claude,nova,llama,openai,any,list-models}`, `agent list/get/memory list`, `tool * session list/show` | `agent {create,invoke,stop,memory clear,tools add}`, `tool browser session {start,stop,navigate,click,screenshot}`, `tool code-interpreter session {start,stop,run}` |
| `cloudtrail` | `aws/cloudtrail/` | none (read-only) | `events {list,show}`, `trail {list,show}` | — |
| `creds` | `aws/creds/` | `SG_AWS__CREDS__ALLOW_MUTATIONS=1` (scope catalogue edits only) | `get`, `list-scopes`, `scope show`, `audit {list,show}` | `scope {add,remove,update}` (catalogue edits) |
| `observe` | `aws/observability/` | none (read-only) | REPL: `sources`, `tail`, `query`, `stats`, `agent-trace`; one-shot equivalents | — |

---

## 2. What's deliberately out (deferred to v0.2.30+)

- **Vault-aware S3 wrappers** (`s3 vault-open / vault-sync / vault-diff / vault-ls`) — depend on the Vault Synchronizer Tool (13 May brief).
- **Container hosts primitive** (`sg-compute container-host/container`) — its own substrate work that uses Slice B's EC2 primitives.
- **Instance-sizing measurement programme** — measurement programme built on top of Slice B's EC2 primitives.
- **Bedrock kb/guardrail/eval/observe/meta/multi-agent/payments** — bound Slice E to the most useful surfaces.
- **IAM graph Phase 4** (CloudTrail-evidence recommendations) — depends on Slice F; cleaner to ship recommendations as a v0.2.30 pack that consumes both.
- **IAM graph Phases 5-6** (per-command lockdown + dog-fooding) — depend on Slice G's scope catalogue being stable.
- **Deployed credential service** (Slice G Phase 5) and **audit dashboard** (Phase 6) — start local, deploy later.
- **AWS dashboard screenshots** (observability addendum) — v2 source.
- **Product analytics layer** + **customer-facing reporting** (observability addendum §4, §6) — built on the substrate this milestone ships.
- **SG billing emission** wiring into observability — depends on the pre-auth payments substrate.

Each of these is real work; this milestone deliberately keeps the substrate clean before layering on top.

---

## 3. The shared shape

Every new surface honours these conventions, enforced by the Foundation PR:

### 3.1 Folder layout

```
sgraph_ai_service_playwright__cli/aws/<surface>/
├── __init__.py                # empty
├── cli/
│   ├── __init__.py            # empty
│   ├── Cli__<Surface>.py      # the Typer/Click sub-group
│   └── verbs/                 # one file per verb when verbs grow logic
├── service/
│   ├── __init__.py
│   └── <Surface>__AWS__Client.py   # wraps Sg__Aws__Session
├── schemas/                   # per-class files
├── enums/                     # per-class files (Enum__*)
├── primitives/                # per-class files (Safe_Str__*, Safe_Int__*)
└── collections/               # per-class files (List__*, Dict__*)
```

### 3.2 The shared client seam

Every `<Surface>__AWS__Client.py` accepts an `Sg__Aws__Session` in its constructor and uses it for every boto3-equivalent call routed via `osbot-aws`. The Foundation PR adds a `Test__Aws__Session__Factory` helper for in-memory composition (no mocks, no patches).

### 3.3 Mutation gate

Every mutating verb starts with:

```python
@spec_cli_errors
@require_mutation_gate('SG_AWS__<SURFACE>__ALLOW_MUTATIONS')
def my_mutating_verb(...):
    ...
```

The `@require_mutation_gate` decorator (Foundation-owned, `aws/Mutation__Gate.py`) reads the env var and raises `Mutation_Gate__Not_Set` with the same Rich-rendered error every existing surface uses today.

### 3.4 Confirmation prompts

Mutating verbs default to `[y/N]` prompts. `--yes` / `-y` skips the prompt. `--dry-run` skips execution entirely and prints the would-be call.

### 3.5 `--json` everywhere

Every verb accepts `--json`. Without it: Rich panel/table. With it: a `Schema__*.json()` to stdout.

### 3.6 Tagging convention

Every resource the CLI creates carries these tags (Foundation-owned, `aws/Aws__Tagger.py`):

| Tag key | Value |
|---------|-------|
| `sg:owner` | from env `SG_AWS__OWNER` (default: `$USER`) |
| `sg:source` | `sg-aws-cli` |
| `sg:created-by` | `<sg-version>:<surface>:<verb>` |
| `sg:created-at` | ISO 8601 UTC |
| `sg:surface` | the surface name (`s3`, `ec2`, `fargate`, etc.) |

This is the precondition for Slice H's observability filters and for the future v0.2.30 leak-sweeper.

### 3.7 Region resolution

A shared `Aws__Region__Resolver` (Foundation) applies the precedence:

```
--region <flag>  >  $AWS_REGION  >  bucket/resource region (when applicable)  >  $SG_AWS__DEFAULT_REGION  >  us-east-1
```

`sg aws acm list` keeps its existing "scan current + us-east-1" behaviour for CloudFront certs.

---

## 4. Where this slots into the reality doc

The Librarian owns the reality-doc updates. Each sibling pack lists, in its `README.md` "Reality doc updates" section, the specific `team/roles/librarian/reality/<domain>/index.md` files it touches. Indicative:

| Sibling pack | Reality-doc domain(s) touched |
|--------------|-------------------------------|
| Foundation | `aws-and-infrastructure/`, `cli-and-orchestration/` |
| S3 | `aws-and-infrastructure/s3.md` (NEW) |
| EC2 | `aws-and-infrastructure/ec2.md` (NEW; supersedes the `scripts/provision_ec2.py` note) |
| Fargate | `aws-and-infrastructure/fargate.md` (NEW) |
| IAM graph | `aws-and-infrastructure/iam.md` (extension) |
| Bedrock | `aws-and-infrastructure/bedrock.md` (NEW), `ai-and-models/` index extension |
| CloudTrail | `aws-and-infrastructure/cloudtrail.md` (NEW), `security-and-audit/` index extension |
| Scoped creds | `security-and-audit/credentials.md` (extension), `aws-and-infrastructure/iam.md` (cross-reference) |
| Observability | `observability/` (NEW domain or extension of existing) |

Each pack updates the reality doc as part of its PR. The Librarian does the final reality-doc cross-reference sweep after the integration→dev merge.

---

## 5. Dependencies between slices

The bulk of the work is independent; only three real dependencies exist, and Foundation paves over two of them:

| Edge | Why | Handled by |
|------|-----|------------|
| Foundation → all sibling packs | Shared scaffold | Foundation merges first; sibling packs fire after |
| Slice A (S3 client) → Slice H (observability uses S3 as a source) | H needs `S3__AWS__Client.list_objects / get_object` | Foundation ships a stub `S3__AWS__Client` interface; A fills it in. H can write its S3 source against the interface in parallel with A. |
| Slice F (CloudTrail client) → Slice H (CloudTrail is a source) | H needs `CloudTrail__AWS__Client.lookup_events` | Same pattern. Foundation ships the interface stub; F fills in; H builds against it. |

No other cross-slice edges. Bedrock, EC2, Fargate, IAM graph, scoped creds all stand alone.

---

## 6. Why this shape

Three principles inherited from v0.2.28:

1. **One slice = one folder = one PR.** Sonnet sub-agents never need to coordinate mid-flight; they merge into an integration branch and the coordinator resolves the (trivial) shared-file conflicts.
2. **The shared scaffold is small and locked.** Foundation ships verb-tree shapes (not bodies), schemas, enums, primitives, the mutation-gate decorator, the tagger, the region resolver, and the source-contract stubs. Per-slice work is "fill in the bodies."
3. **Type_Safe everywhere from day one.** Every new schema, every new enum, every new primitive lives in its own file. No retroactive cleanup later.

---

## 7. Risk surface (architecture-level)

Per-slice risks live in each sibling pack's `README.md` "Risks to watch" section. The architecture-level risks the umbrella owns:

| Risk | Mitigation |
|------|-----------|
| Two slices invent overlapping schemas for AWS-shared concepts (a Tag, an ARN, a Region) | Foundation ships canonical `Schema__AWS__Tag`, `Safe_Str__AWS__ARN`, `Safe_Str__AWS__Region` — sibling packs reuse, never redefine |
| A slice ships a direct boto3 call to "make it work" | Code review enforces CLAUDE.md rule #14; the Foundation `Sg__Aws__Session` helpers make the right path the easy path |
| A slice's mutation gate is named inconsistently | Foundation owns the decorator; each slice passes its env var name as the decorator argument |
| Bedrock model-ID resolution drift between regions | Slice E owns a `Bedrock__Model__Resolver` that's the single source of truth; a per-region alias table lives in a vault and is reviewed |
| Slice G's scope catalogue clashes with existing IAM roles | The scope catalogue refuses to create a scope whose underlying role name already exists outside the `sg-scope-*` prefix; reviewed in code review |
| Observability REPL leaks credentials into command history | Session captures redact `AWS_*` env vars by default; documented in Slice H |

---

## 8. Pointer back

For the locked decisions, sign-off checklist, and the sibling pack index, see the [umbrella README](README.md). For the orchestration plan see [`03__sonnet-orchestration-plan.md`](03__sonnet-orchestration-plan.md). For the Foundation brief itself see [`02__common-foundation.md`](02__common-foundation.md).
