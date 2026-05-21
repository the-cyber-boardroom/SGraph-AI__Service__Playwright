---
title: "The TUI API — contract, conventions & the unified data model"
file: 01__tui-api-contract-and-conventions.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 14)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PROPOSED — does not exist yet. Standard for ratification; the cross-tool reference the two voice-memo briefs ask for.
scope: platform-wide standard (not specific to the Bedrock chat). The chat is its first consumer + first provider.
grounds_on:
  - "voice-memo brief 1: v0.27.55__arch-brief__tui-api-structured-surface-for-text-uis (the outbound surface + dev sequence + TUI-of-TUIs)"
  - "voice-memo brief 2: v0.27.55__arch-brief__tui-api-extensions (multi-API-per-tool, native IAM/tokens, sequencing, orientation, change-control, VFS)"
  - "team/humans/dinis_cruz/claude-code-web/05/21/10/v0.2.36__bedrock-chat-tui-pack/05__tui-api-tools-and-documents-plan.md (the chat's tools plan — source of the execution-center, loadout, dry-run, cost material)"
  - library/guides/v0.2.39__tui_cli_separation.md   # 'a TUI is a GUI over the CLI'
  - "memory_fs (PyPI, Python 3.12) — the VFS substrate; verified CRUD this session"
  - sgraph_ai_service_playwright__cli/credentials/ + aws/creds/  # the privilege / scoped-creds substrate
supersedes_in_part: "v0.2.36__bedrock-chat-tui-pack/05 §1–8 (the generic contract is lifted here; 05 is being slimmed to chat-specific consumption)"
---

# The TUI API — contract & conventions

> **PROPOSED — does not exist yet.** This is the platform standard extracted from the
> Bedrock chat pack (doc 05) and merged with the two TUI-API voice-memo briefs. Its job is
> to **lock the unified data model** — one contract that serves both directions and carries
> the briefs' IAM/sequencing/orientation/change-control/VFS mechanics *and* the chat pack's
> cost / controlled-execution additions. Nothing here is built yet except the noted
> substrates (`memory_fs`, the credentials machinery, the chat TUI as the pilot host).

---

## 1. The thesis, in one paragraph

A **TUI API** is the structured surface that makes a text UI machine-readable, composable,
and consumable — by humans, by pytest, by other TUIs, and by LLM agents alike. It is the
Python/terminal mirror of the shipped SGraph **JS Tool API** (`window.__tool` /
`manifest.api.actions` / `SKILL-*.md`), and the same principle as this repo's
`v0.2.39__tui_cli_separation.md` ("a TUI is a GUI over the CLI; the UI owns no logic").
Every tool exposes one **or more** TUI APIs; every TUI API is **discoverable, scoped by
capability tokens, sequenced, self-describing, and audited**; and any tool is therefore both
a **provider** of its own surface and a **consumer** of others' — the fractal that made
vaults-of-vaults viable, one layer up (tools-of-tools).

---

## 2. Two directions of one contract (the framing the briefs forced)

The same contract is used by a **provider** (exposes actions/state/events) and a **consumer**
(discovers and invokes them). A given TUI is usually both:

| Role | Brief | What it does | Example |
|---|---|---|---|
| **Provider** (outbound) | brief 1 | exposes *its own* state, actions, events, screens, export, orientation | `sg edge tui` exposes `deployment` / `slugs` / `admin` APIs to be driven |
| **Consumer** (inbound) | bedrock pack 05 | discovers providers, builds a scoped loadout, invokes through an execution center | the Bedrock chat calls `sg-edge.slugs.wake` mid-conversation |

The Bedrock chat is the pilot for **both**: it consumes host providers (the tools the model
calls) **and** exposes its own provider surface (its session/cost/transcript state is
queryable; `send`/`clear`/`set-model`/`export-brief` are invocable; turn/cost events are
subscribable). Building the chat without its provider surface is the "redo it later" trap
both briefs name — so the provider seam is v1, not v2.

---

## 3. The development sequence this standard assumes

`capability → CLI → TUI → Web API → Web UI` (brief 1). The TUI is the cheap middle step
most projects skip, paying the highest cost (web UI) first. This standard makes the **TUI +
TUI API** the default next step after the CLI. The TUI API is *not just the CLI repackaged*:
the CLI exposes atomic actions at maximum granularity; the TUI API exposes **use-case-focused,
stateful, sequenced** capabilities. Both are agent surfaces; they serve different agent needs.

---

## 4. The unified data model (Type_Safe; one class per file in the build)

Shown compactly. Generic + reusable → live in dev's shared lib at `cli/tui/tool_api/`.
Every `input_schema`/`output_schema`/`payload_schema` is **real JSON Schema derived from a
Type_Safe params class** (osbot-utils can emit it) — strict, drift-free, one source of truth
shared with the JS manifests.

### 4.1 Capability ladder, scopes, and privileges (the IAM reconciliation)

The briefs want **capability tokens** (`sg-edge:slugs:write`, time-bounded, delegable); the
chat pack modelled **AWS IAM** (policy/role/vault-key). They are two layers, not a conflict:
a **scope** is the user-facing capability token; a **privilege** is the backing grant the
scope *maps down to* when the action actually touches AWS/vault/network.

```python
Enum__Tui_Api__Tier:  READ_ONLY · WRITE · CRUD · DESTRUCTIVE          # coarse capability ladder

Schema__Tui_Api__Scope:                                              # the capability token (brief 2)
    api        : str           # owning API slug, e.g. 'sg-edge.slugs'
    capability : str           # fine verb or tier, e.g. 'read' | 'write' | 'wake' | 'terminate'
    resource   : str = '*'     # optional qualifier, e.g. a slug glob
    # string form: '{api}:{capability}[:{resource}]'  — what a Simple Token carries

Schema__Tui_Api__Privilege:                                          # the backing grant a scope maps to
    kind : Enum__Tui_Api__Priv_Kind   # SIMPLE_TOKEN | IAM_POLICY | IAM_ROLE | VAULT_KEY | ENV | NETWORK | OTHER
    ref  : str                        # token id / policy ARN / role ARN / vault key / env var
    note : str

Schema__Tui_Api__Grant:                                              # a scope granted to an identity, time-bounded
    scope      : Schema__Tui_Api__Scope
    expires_at : float = 0            # 0 = session lifetime; else epoch (hour / workflow bound — brief 2)
    derived_from : str = ''           # parent token id, for sub-agent delegation (brief 2)
```

### 4.2 Sequencing — conditional gating (brief 2; the safety mechanic)

An action is **available** only when its preconditions hold against the provider's current
state. Discovery returns *only available actions*, so an out-of-sequence call is invisible to
the model, not merely refused.

```python
Schema__Tui_Api__Precondition:
    state_path : str                  # dotted path into provider.state(), e.g. 'slug.state'
    op         : Enum__Tui_Api__Cond_Op   # EQ | NEQ | IN | NOT_IN | EXISTS | ABSENT
    value      : str                  # or a small list for IN/NOT_IN
    note       : str                  # human reason, surfaced on refusal
# e.g. terminate-instance: [{state_path:'slug.state', op:EQ, value:'live'}]
```

### 4.3 Action, event, manifest

```python
Schema__Tui_Api__Action:
    name             : str
    description      : str            # short; deep prose lives in SKILL-api.md (in the VFS)
    input_schema     : dict           # REAL JSON Schema (from a Type_Safe params class)
    output_schema    : dict
    tier             : Enum__Tui_Api__Tier
    scope            : Schema__Tui_Api__Scope          # capability token required to invoke
    privileges       : List__Tui_Api__Privilege        # backing grants consumed (overrides API baseline)
    preconditions    : List__Tui_Api__Precondition     # sequencing/state gates (§4.2)
    idempotent       : bool
    supports_dry_run : bool
    emits            : List[str]       # event names this action can raise
    est_cost_usd     : float = 0       # static hint; the execution center records actual (§7)

Schema__Tui_Api__Event:
    name           : str
    description    : str
    payload_schema : dict

Schema__Tui_Api__Manifest:            # ONE per TUI API (a tool has many — §4.4)
    slug       : str                   # 'sg-edge.slugs'
    tool       : str                   # 'sg-edge' (owning tool)
    name, version, description
    tiers      : List__Tui_Api__Tier
    scopes     : List__Tui_Api__Scope          # capability tokens this API defines
    privileges : List__Tui_Api__Privilege       # API-level baseline backing grants
    actions    : List__Tui_Api__Action
    events     : List__Tui_Api__Event
    skills     : Schema__Tui_Api__Skills         # refs to SKILL-{human,api,driver} (VFS paths)
    children   : List[str]                       # fractal: sub-API slugs this one composes
```

### 4.4 Multiple TUI APIs per tool + orientation (brief 2 mechanics 1 + 3)

A **tool** is not one API — it is a cluster, each API standing on its own with its own scope,
docs, and changelog (the microservice-vs-monolith decomposition). The tool descriptor binds
them and carries the **orientation surface** (the "now what?" answer).

```python
Schema__Tui_Api__Tool:
    slug        : str                  # 'sg-edge'
    name, version, description
    apis        : List[str]            # ['sg-edge.deployment','sg-edge.slugs','sg-edge.admin', ...]
    vfs_root    : str                  # '/tools/sg-edge/'  (§6)
    orientation : Schema__Tui_Api__Orientation

Schema__Tui_Api__Orientation:         # answers 'I just arrived — now what?'
    status            : dict           # health + what it's doing right now
    available_actions : List[str]      # given current state + the caller's grants
    whatsnew_ref      : str            # VFS path: /tools/<tool>/whatsnew.md
    coming_soon_ref   : str
    known_issues_ref  : str
    common_workflows  : List[str]      # workflow names (§5)
    skills_ref        : str            # /tools/<tool>/skills.md
# Delivered as: describe (static manifest) + status (live) + the VFS doc tree (§6).
```

### 4.5 Change control as a surface (brief 2 mechanic 4)

```python
Enum__Tui_Api__Change_Kind:  FEATURE · FIX · DEPRECATION · BREAKING · CONFIG

Schema__Tui_Api__Change:
    kind    : Enum__Tui_Api__Change_Kind
    summary : str
    version : str
    ts      : float
# Structured artefacts captured at the moment of change; rendered into changelog.md /
# whatsnew.md in the VFS. CI enforces: a shipped FEATURE with no Change entry fails the build.
```

### 4.6 Consumer side — loadout & workflow assembly (brief 2; pack 05 §4)

The model **never** picks its own tools ("not to have the agent designing what tools to
use"). A **workflow** is the curated source of truth; the system assembles a **loadout**
(a time-bounded set of grants) from it.

```python
Schema__Tui_Api__Workflow:            # the curation unit, e.g. 'diagnose-edge-issue'
    name, description
    apis     : List[str]              # included API slugs
    grants   : List__Tui_Api__Grant   # capability tokens handed to the agent
    excluded : List[str]              # explicitly excluded APIs (documented, for clarity)

Schema__Tui_Api__Loadout:             # the assembled, live grant set the chat operates under
    grants   : List__Tui_Api__Grant
    workflow : str                    # provenance: which workflow assembled this
    budget_usd : float = 0            # optional spend ceiling for the whole loadout (cost — §7)
    def tool_config(self)         -> dict   # Bedrock toolConfig: only granted, in-tier, available actions
    def skills_markup(self)       -> str    # concatenated SKILL-api prose for the system prompt
    def required_privileges(self) -> List__Tui_Api__Privilege   # union, for the pre-flight
```

### 4.7 Execution center, result & audit (pack 05 §5 — the controlled core)

```python
Enum__Tui_Api__Exec_Mode:  AUTO · CONFIRM · DRY_RUN

Schema__Tui_Api__Result:
    ok       : bool
    data     : dict
    error    : str
    dry_run  : bool
    preview  : dict        # change-set / field-diff when dry-run or WRITE-without-ALLOW_MUTATIONS
    cost_usd : float       # actual cost attributed to this call (§7)

Schema__Tui_Api__Call:                # the audit ring-buffer record (getLog() analogue)
    action_ref : str
    params     : dict      # sanitised — secrets masked (mirror JS sanitiseParams)
    scope_used : Schema__Tui_Api__Scope
    mode       : Enum__Tui_Api__Exec_Mode
    result_ok  : bool
    error      : str
    duration_ms: int
    cost_usd   : float
    identity   : str       # who/what called (token subject)
    ts         : float

class Tui_Api__Execution_Center(Type_Safe):
    mode      : Enum__Tui_Api__Exec_Mode
    registry  : Tui_Api__Registry
    tokens    : Tui_Api__Token__Resolver     # over credentials/ + aws/creds/ scoped-creds
    log       : List__Tui_Api__Call          # ring buffer → the Inspector
    def execute(self, action_ref, params, on_preview=None, on_confirm=None) -> Result:
        # 1. resolve action → tier, scope, privileges, preconditions, supports_dry_run
        # 2. precondition check against provider.state(); refuse (with note) if not available
        # 3. validate params against the action's JSON Schema (deterministic, early)
        # 4. token pre-flight: caller holds the required scope (unexpired); else refuse
        # 5. privilege pre-flight: scope maps to present IAM/vault/env; else print minimal policy
        # 6. preview: DRY_RUN or (tier>=WRITE without ..._ALLOW_MUTATIONS) → provider dry-run → change-set
        # 7. gate: CONFIRM or tier>=WRITE/DESTRUCTIVE → surface preview (action·args·tier·scope·diff) → await
        # 8. dispatch: provider.dispatch(action, params, mode) → Result
        # 9. audit: append a sanitised Call; attach cost (model round-trips + API $)
```

### 4.8 The provider seam (the dual-role interface every host implements)

```python
class Tui_Api__Provider(Type_Safe):
    def manifest(self)                  -> Schema__Tui_Api__Manifest      # describe (static)
    def skills(self)                    -> dict                          # {human, api, driver} markdown
    def state(self)                     -> dict                          # outbound 'state' (brief 1)
    def actions_available(self, grants) -> List__Tui_Api__Action         # filtered by preconditions + scope
    def dispatch(self, action, params, mode) -> Schema__Tui_Api__Result
    def events(self)                    -> 'iterator'                     # 'watch' — NDJSON stream (brief 1)
    def export(self, view, fmt)         -> bytes                          # 'export' (brief 1)
    def orientation(self)               -> Schema__Tui_Api__Orientation   # 'now what?' (brief 2)
    def populate_vfs(self, vfs)         -> None                           # write its doc tree (§6)
```

A central `Tui_Api__Registry` enumerates providers by walking the `sg`/`sp` command tree, so
the chat, the explorer, pytest, and the CLI all read **one** source of truth. Fractal: a
provider may compose children (`manifest.children`); v1 supports one level and renders the tree.

---

## 5. CLI surface (discovery = `sg <area> tui api`)

`api` is a **sub-command of `tui`** (ratified — not a new top-level verb). Same dispatch the
chat and the explorer use; driveable by human, pytest, and model:

```
sg <area> tui api list                      # the APIs this tool exposes
sg <area> tui api describe [<api>] [--json] # the manifest (actions·tiers·scopes·privileges·preconditions)
sg <area> tui api status   [<api>]          # live orientation: health, available actions, whatsnew
sg <area> tui api skills   <human|api|driver>
sg <area> tui api state    [--screen X]     # current display state as structured data (brief 1)
sg <area> tui api invoke   <action> --params '{...}' [--dry-run]
sg <area> tui api watch                     # NDJSON event stream (brief 1)
sg <area> tui api export   [--screen X] [--format json]
sg <area> tui api whatsnew | changelog      # the change-control surface (brief 2)
```

---

## 6. The VFS — context without pollution (brief 2 mechanic 5)

The orientation surface and the change-control surface are **delivered through a virtual
filesystem**, not stuffed into the model's context window. The agent sees a *directory*; it
reads only what it needs (`vfs.read`) — **files as a tool, not as context**. 500 reference
files cost ~zero tokens until three are opened.

- **Substrate:** `memory_fs` (PyPI, Python 3.12 — aligned with this repo). Verified this
  session: a CRUD round-trip over `Storage_FS__Memory` works out of the box. Default backend
  is `Storage_FS__Memory` (ephemeral, no creds); swap to `Local_Disk` / `Sqlite` / `Zip` / S3
  to persist (one constructor change). It is **also** a TUI API itself (the VFS core tool):
  `vfs.list/tree/read/stat` (READ_ONLY) · `vfs.write/mkdir/move` (WRITE) · `vfs.delete/clear`
  (DESTRUCTIVE) — disabled by default, granted per workflow.
- **Standard tree, tool-populated at startup** (the convention every tool follows):

```
/tools/<tool>/
  skills.md            # how to use this tool well (always-relevant, small — read first)
  changelog.md         # structured change history
  whatsnew.md          # highlights since last visit
  coming-soon.md       # in-development capabilities
  known-issues.md      # current limitations
  current-state.json   # a state snapshot (the 'state' surface, materialised)
  workflows/<name>.md  # one per curated workflow (§5)
  api/<api-slug>.json  # one manifest per TUI API this tool exposes
```

Conventions are opinionated on purpose (brief 2): files carry a relevance/size hint so the
agent reads small high-signal files first; the FS is **per-session scoped**; default
ephemeral. This composes with document attachments — attach when the model must read *now*;
VFS when it should read *on demand*.

---

## 7. Cost — the cross-cutting concern the briefs omit (keep + extend)

The briefs say nothing about cost; the chat pack makes it first-class, and this standard
keeps it. Every `Schema__Tui_Api__Call` records `cost_usd`; a single agent turn may be N model
round-trips + M tool calls, and the **per-turn cost sums all sub-calls**. Cost aggregates at
three levels: **per-call** (audit), **per-turn** (the chat meter), **per-loadout/workflow**
(an optional `budget_usd` ceiling, §4.6). This is the controlled-execution story MCP-style
all-or-nothing exposure cannot give.

---

## 8. Relationship to MCP (brief 2 is explicit)

**Not an MCP replacement; interoperates where useful.** The differentiators are exactly the
mechanics above: MCP tends toward all-or-nothing tool exposure; the TUI API gives **granular
capability scopes**, **state-based sequencing** (the model literally cannot see an
out-of-sequence action), **dry-run/confirm gating**, **cost attribution**, and **VFS
context-without-pollution**. A later bridge provider can satisfy this contract over MCP/HTTP
for non-Python tools, with the same scoping/sequencing/audit applied at the boundary.

---

## 9. Module placement

| Piece | Home | Why |
|---|---|---|
| Contract types, registry, execution center, token resolver, loadout, workflow assembly | `cli/tui/tool_api/` | generic + reusable; aligns with dev's shared `cli/tui/` lib |
| Core tools (VFS now; web-fetch / code-exec later) | `cli/tui/tool_api/core/` | reusable; VFS wraps `memory_fs` (new dependency, 3.12) |
| Provider base + the dual seam (`Tui_Api__Provider`) | `cli/tui/tool_api/` | every host subclasses it |
| Each host's provider(s) + SKILL files + change records | with the host (`sg_edge/.../tui_api/`, `aws/s3/.../tui_api/`) | co-located with the capability |
| Bedrock-chat-specific glue (toolConfig builder, engine tool-loop, doc attach) | `aws/bedrock/tui/` | provider-specific (see pack 05) |

---

## 10. Decisions to ratify (before building)

| # | Decision | Recommendation |
|---|---|---|
| 1 | Scope ↔ privilege mapping depth | v1: scope is a Simple Token; privilege pre-flight is presence/role check + print-policy on miss. Live `iam:SimulatePrincipalPolicy` later. |
| 2 | Token substrate | Reuse the credential-manager Simple Tokens; scopes are `{api}:{capability}[:{resource}]`; time-bounds + sub-agent derivation are first-class. |
| 3 | Sequencing expressiveness | v1: flat preconditions over `provider.state()` (EQ/IN/EXISTS…). No DAG/workflow-engine yet. |
| 4 | Orientation file name | `skills.md` (continuity with the vault-app JS convention), not `README.md`. |
| 5 | Change-capture enforcement | Mandatory for shipped FEATURE/BREAKING; CI fails if absent; LLM-assisted drafting allowed. |
| 6 | VFS default persistence | Ephemeral `Storage_FS__Memory`; `--vfs-backend local\|sqlite\|s3` to persist; document lose-on-close in SKILL-human. |
| 7 | Multi-API granularity | Per-API scope by default; per-action scope where the action is DESTRUCTIVE. |
| 8 | Provider surface in v1 | Yes — the chat exposes its own state/actions/events from the first slice (avoids the redo trap). |
| 9 | JSON Schema source of truth | Derive from Type_Safe (Python) + enrich the JS manifests to match → one shared definition. |
| 10 | Can the chat change its own loadout? | No. Loadout is human/workflow-curated; the model requests, the human/workflow grants. |

---

## 11. What's real vs PROPOSED (honesty)

| Thing | Status |
|---|---|
| `memory_fs` VFS substrate (Memory/Local/Sqlite/Zip backends) | **EXISTS** (PyPI, 3.12; CRUD verified this session) |
| Credentials / scoped-creds machinery | **EXISTS** (`credentials/`, `aws/creds/`) |
| Bedrock chat TUI (engine, cost model, inspector) | **EXISTS** on this branch (the pilot host) |
| `Bedrock__Cost__Calculator`, model aliases, stream adapter | **EXISTS** |
| Everything in §4–§9 (the contract, execution center, tokens, sequencing, orientation, change-control, workflow assembly, the VFS *conventions* layer) | **PROPOSED — does not exist yet** |
| Simple Tokens scoped to TUI APIs | **PROPOSED** (the credential manager exists; the scope mapping does not) |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
