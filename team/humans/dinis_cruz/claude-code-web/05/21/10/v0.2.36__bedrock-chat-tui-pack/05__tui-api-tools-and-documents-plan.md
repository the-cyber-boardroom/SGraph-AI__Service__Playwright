---
title: "Bedrock Chat TUI — TUI API, tool execution & document support plan"
file: 05__tui-api-tools-and-documents-plan.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 12)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — design for ratification. Mirrors the SGraph JS Tool API on the Python/TUI side.
parent: README.md
grounds_on:
  - "SGraph JS Tool API bundle (sg-tool-api): manifest.api.actions + SKILL files + discover→dispatch loop"
  - sgraph_ai_service_playwright__cli/tui/                     # dev's shared component-first TUI lib (Tui__App, Debug Panel)
  - library/guides/v0.2.39__tui_cli_separation.md             # 'a TUI is a GUI over the CLI' — same principle, other side
  - sgraph_ai_service_playwright__cli/credentials/ + aws/creds/  # privilege / scoped-creds machinery
---

# TUI API, tool execution & document support

> **The one idea.** Wherever the chat is embedded, the host hands it a **TUI API** — a
> machine-readable contract (`actions` + real JSON Schema) plus **skills** (prose that
> teaches the model how to use them) plus **required privileges**. The chat is just a
> consumer. This is the Python/terminal mirror of the shipped SGraph **JS Tool API**
> (`window.__tool` / `manifest.api.actions` / `SKILL-*.md`). Same contract shape, different
> runtime — and the same principle as the repo's "a TUI is a GUI over the CLI" guide.

This plan covers: the TUI API contract, how it's discovered (a CLI command/class),
capability tiers tied to IAM privileges, the **loadout** (choosing which TUI APIs to
expose to a chat), the **tool execution center** (auto / confirm / dry-run, privilege-
gated, real-or-simulated, audited), the chat's tool-use loop, a **Swagger-style TUI API
explorer/tester**, and document support.

---

## 1. The principle (and why it's not a coincidence)

The JS Tool API's thesis — *"a tool is an API first, a UI second; the browser UI,
Playwright, the console, and an LLM agent are all equal consumers"* — is identical to
this repo's `v0.2.39__tui_cli_separation.md` ("a TUI is a GUI over the CLI; the UI owns
no logic; nothing is TUI-exclusive"). So the TUI API is the same contract from the
Python side:

| JS Tool API (browser) | TUI API (this plan, Python) |
|---|---|
| `window.__tool` registry | a CLI command / `Tui_Api__Provider` class (in-process, no `window`) |
| `manifest.api.actions` (loose params) | `Schema__Tui_Api__Action` with **real JSON Schema** |
| `SKILL-{human,browser,api}.md` | `SKILL-{human,api,driver}.md` (same three audiences) |
| `api.meta.getManifest/getSkills/getMethods/getEvents` | `Tui_Api__Provider.manifest()/skills()/actions()/events()` |
| `api[name](params) → Promise` | `Tui_Api__Provider.dispatch(name, params, mode)` |
| `api.meta.getLog()` ring buffer | the execution center's audit log → the Inspector |
| dev panel (console/explorer/manifest) | the **Swagger-style TUI API tester** (§7) |

Decisions confirmed with the owner:
1. **Registry + tool definitions live in the CLI** — a command (or class) callable from
   the Python TUI that yields the manifest, skills, action defs, and **required privileges**.
2. **Real JSON Schema** for every action input — for deterministic model output.

---

## 2. The TUI API contract

Type_Safe schemas (one class per file in the build; shown compactly here). Generic +
reusable → live in dev's shared lib at `cli/tui/tool_api/`.

```python
Enum__Tui_Api__Tier:  READ_ONLY · WRITE · CRUD · DESTRUCTIVE        # capability ladder

Schema__Tui_Api__Privilege:                                         # fractal: API-level or per-action
    kind : Enum(IAM_POLICY | IAM_ROLE | VAULT_KEY | ENV | NETWORK | OTHER)
    ref  : str            # policy ARN / role ARN / vault key id / env var name
    note : str

Schema__Tui_Api__Action:                                            # ≈ one api.actions entry / one Bedrock toolSpec
    name             : str
    description      : str            # short; the deep prose lives in SKILL-api.md
    input_schema     : dict           # REAL JSON Schema (properties + required + enums)
    output_schema    : dict           # optional
    tier             : Enum__Tui_Api__Tier
    privileges       : List__Tui_Api__Privilege   # overrides manifest-level if set
    idempotent       : bool
    supports_dry_run : bool           # can the execution center preview it without committing?
    events           : List[str]

Schema__Tui_Api__Manifest:
    name, slug, version, description
    tiers      : List[Enum__Tui_Api__Tier]        # which tiers this API offers at all
    privileges : List__Tui_Api__Privilege         # API-level baseline privs
    actions    : List__Tui_Api__Action
    events     : List__Tui_Api__Event
    skills     : Schema__Tui_Api__Skills          # refs to SKILL-human / -api / -driver
    children   : List[str]                         # fractal: sub-API slugs this one composes
```

### Real JSON Schema, for free
On the Python side an action's `input_schema` is **derived from a Type_Safe params
class** (osbot-utils can emit JSON Schema), so strict schema is automatic and matches
the repo's Type_Safe-everywhere rule — no hand-written, drift-prone JSON. On the shared
side, this is the JS bundle's option (b): enrich the manifests to carry real JSON Schema
so the browser and the TUI share **one** source of truth (the owner agreed).

### Skills (three audiences, mirroring the JS pattern)
`SKILL-human.md` (what it is / when to reach for it), `SKILL-api.md` (the precise machine
spec — signatures, returns, errors, limits; this is what goes to the model), `SKILL-driver.md`
(how to drive it from Python/CLI, the analogue of `SKILL-browser.md`).

---

## 3. Discovery — the TUI API lives in the CLI

Each host area exposes its TUI API as a **CLI command + a provider class** (satisfies
"GUI over the CLI" — nothing TUI-exclusive):

```
sg <area> tui-api list                 # what APIs/actions exist here
sg <area> tui-api manifest [--json]    # the manifest (actions + tiers + privileges)
sg <area> tui-api skills <human|api|driver>
sg <area> tui-api invoke <action> --params '{...}' [--dry-run]   # the same dispatch the chat uses
```

```python
class Tui_Api__Provider(Type_Safe):          # the seam every host implements
    def manifest(self)            -> Schema__Tui_Api__Manifest: ...
    def skills(self)              -> dict:    # {human, api, driver} markdown
    def dispatch(self, action, params, mode) -> Schema__Tui_Api__Result: ...
```

A central `Tui_Api__Registry` enumerates providers (walking the `sg`/`sp` command tree),
so the chat reads exactly what `sg <area> tui-api` exposes — one source of truth, driveable
by a human, by pytest, and by the model alike.

**Fractal.** A provider may compose child providers (`manifest.children`); the registry
flattens or presents the tree. v1: support one level of nesting and render the tree;
deeper nesting is a later concern (flagged, not built).

---

## 4. The loadout — choosing which TUI APIs the chat gets

You never dump every capability on the model. Before (or during) a chat, the user — **or
a host tool** — selects which TUI APIs, and **at which tier**, to expose. This is the
privilege-aware scoping the owner asked for.

```python
Schema__Tui_Api__Loadout:
    selected : Dict[str, Enum__Tui_Api__Tier]    # api_slug → max tier granted
    def tool_config(self)  -> dict:              # Bedrock toolConfig: only selected actions ≤ granted tier
    def skills_markup(self) -> str:              # concatenated SKILL-api prose for the system prompt
    def required_privileges(self) -> List__Tui_Api__Privilege   # union, for the pre-flight check
```

UX (a loadout modal, `ctrl+t`-style key, plus a `--tools edge:read-only,s3:read-only` CLI flag):

```
┌─ choose TUI APIs for this chat ──────────────────────────────────────────────┐
│  api            tier offered                granted        privileges          │
│ ▸ sg edge       READ_ONLY · WRITE           [READ_ONLY ▾]  (none)              │
│   sg aws s3     READ_ONLY · CRUD            [READ_ONLY ▾]  iam: s3:List*,Get*  │
│   sg aws ec2    READ_ONLY · DESTRUCTIVE     [ off       ▾]  iam: ec2:* (role)  │
│                                                                                │
│  granting WRITE+ shows the IAM privs that must be present · esc apply          │
│  [space] cycle tier   [enter] apply   only granted actions reach the model     │
└────────────────────────────────────────────────────────────────────────────────┘
```

Only actions at or below the granted tier are compiled into the model's `toolConfig`, and
only their SKILL prose is injected — so an unselected/over-tier capability is invisible to
the model, not merely refused at call time.

---

## 5. The tool execution center — controlled, real-or-simulated, audited

The heart of the design. A single `Tui_Api__Execution_Center` mediates **every** tool
call (whether the model requested it or a human clicked it in the tester). It is reusable
and lives in `cli/tui/tool_api/`.

```python
Enum__Tui_Api__Exec_Mode:  AUTO · CONFIRM · DRY_RUN

class Tui_Api__Execution_Center(Type_Safe):
    mode       : Enum__Tui_Api__Exec_Mode
    registry   : Tui_Api__Registry
    privileges : Tui_Api__Privilege__Resolver       # reuses credentials/ + aws/creds/ scoped-creds
    log        : List__Tui_Api__Call                 # ring buffer (the getLog() analogue)

    def execute(self, action_ref, params, on_preview=None, on_confirm=None):
        # 1. resolve action → tier, privileges, supports_dry_run
        # 2. validate params against the action's JSON Schema (reject early, deterministic)
        # 3. privilege pre-flight: resolver checks the active identity has the required
        #    IAM policy / role / vault key / env; refuse with an actionable hint if not
        #    (mirrors the existing _render_bedrock_client_error pattern)
        # 4. preview: if DRY_RUN, or tier ≥ WRITE without ..._ALLOW_MUTATIONS, run the
        #    provider's dry-run → a change-set/field-diff preview (playbook §6 simulate)
        # 5. gate: if CONFIRM (or tier ≥ WRITE/DESTRUCTIVE), surface the preview in a
        #    confirm modal showing action · args · tier · privs · predicted change; await
        # 6. dispatch: provider.dispatch(action, params, mode) → result
        # 7. audit: append a sanitised Call record (secrets masked like JS sanitiseParams);
        #    attach cost if the call triggered model round-trips
```

Key behaviours the owner called for:

- **Auto vs manual.** `mode` is per-session and per-tier: e.g. AUTO for READ_ONLY,
  CONFIRM for WRITE+, never silent for DESTRUCTIVE. Configurable.
- **Real vs simulated.** A tool's *effect* is decided here. `supports_dry_run` actions can
  preview the change-set before committing; real mutations stay gated behind the existing
  `..._ALLOW_MUTATIONS` env (consistent with `sg aws s3`/`cf`).
- **Privilege-gated.** Required privileges are declared in the manifest (API-level and/or
  per-action) and enforced before execution; missing privileges → a refusal that prints
  the minimal IAM policy needed (reuse `sg aws ... --print-policy` style).
- **Audited.** Every call (params sanitised, tier, mode, privs used, result/error,
  duration, cost) lands in the ring buffer → rendered in the Inspector (§6).

---

## 6. Chat integration — the tool-use loop + the Inspector

The engine's `send_turn` grows a **Converse tool loop**:

```
build toolConfig from the loadout  →  converse
model emits stopReason='tool_use' (one+ toolUse blocks)
  → for each: execution_center.execute(name, input)   (mode/priv/dry-run policy applies)
  → append toolResult content blocks
  → converse again
repeat until stopReason='end_turn'
```

Every model round-trip and every tool call is recorded; **the per-turn cost sums all
sub-calls** (a single user turn may be N Converse calls + M tool calls — critical given
the cost focus). The cost meter gains a per-turn "calls: 3 model · 2 tools" line.

The **Inspector** I already built is the natural surface — it already shows the exact
request/response per turn. Extend it to render `toolUse` / `toolResult` blocks inline and
to show the execution center's audit entries (this is the TUI twin of the JS
`getGenerations()` / dev panel). Tool calls also render as collapsible blocks in the
transcript (call · args · tier · result, with a ⚠ marker if simulated).

---

## 7. The Swagger-style TUI API explorer/tester

The owner asked for a way to **manually and automatically test** TUI APIs — the analogue
of the JS `sg-tool-api-{console,explorer,manifest}` components and Swagger UI. A reusable
screen + a pytest harness, both driving the **same** registry + execution center as the chat.

**Manual (explorer/console screen — `sg ... tui-api explore` / a TUI screen):**
```
┌─ TUI API Explorer ──────────────────────────┬─ action: sg aws s3 · list_objects ──────────┐
│ ▾ sg edge            READ_ONLY WRITE          │ tier READ_ONLY   privs iam:s3:List*,Get*    │
│     register_slug    WRITE                    │                                              │
│   ▾ sg aws s3        READ_ONLY CRUD           │ input (JSON Schema form)                     │
│ ▸     list_objects   READ_ONLY  ◀ selected    │   bucket* [..................]               │
│       get_object     READ_ONLY                │   prefix  [..................]               │
│       put_object     WRITE                    │   mode    (•) dry-run  ( ) real              │
│   ▾ sg aws ec2       READ_ONLY DESTRUCTIVE    │                                              │
│       terminate      DESTRUCTIVE  ⚠           │ [enter] invoke → result + audit entry        │
│                                              │ SKILL-api ▾   manifest ▾   last result ▾     │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```
Pick an action → see its JSON Schema (as a form), SKILL prose, tier, and privileges → fill
params → choose dry-run/real → invoke through the execution center → see result + the audit
entry. This is "Swagger for the TUI API," and it doubles as the manual QA surface.

**Automated (pytest, no mocks — the project's deploy-via-pytest culture):** for every
registered provider, assert: the manifest validates; every action carries real JSON Schema
(properties + required); privileges are declared for any tier ≥ WRITE; `supports_dry_run`
actions actually preview without committing; sample inputs schema-validate; the SKILL files
exist and name every action. In-memory providers make this run with no AWS.

---

## 8. Privileges — first-class in the contract

- Declared in the manifest: **API-level baseline** + optional **per-action override** (fractal).
- A `Tui_Api__Privilege__Resolver` checks the active identity against required privileges,
  reusing the existing `credentials/` + `aws/creds/` scoped-creds machinery. On a miss it
  prints the minimal policy/role needed and refuses (never a silent failure).
- The loadout shows privileges next to each tier so granting WRITE+ is an informed choice.
- This makes "what IAM does this chat need?" answerable up front: `loadout.required_privileges()`
  is the union for the whole session.

---

## 9. Document support (settled scope)

Two capabilities, both feeding the existing context/attachment seams:

1. **Converse document attachments** — attach a file (pdf / txt / md / csv / docx / html /
   xls(x)) to a message; Nova reads it natively via Converse `document` content blocks
   (`{document: {format, name, source: {bytes}}}`). A file-picker modal (`ctrl+d`), an
   attached-docs chip row above the composer, and the **added input-token cost surfaced**
   per turn (and visible in the Inspector — the document is part of the exact request).
   Respect Bedrock limits (≤ ~4.5 MB, ≤ 5 docs/message); reject oversize with a clear hint.
2. **Persistent session context** — extend the existing `--context` seam so one or more
   docs stand as context for the whole session (system block), labelled `[SEEDED]` in the
   meter (already implemented for a single context; generalise to N docs + the picker).

**RAG (chunk/retrieve) is explicitly out** for v1 — noted as a later phase (needs an
embedding store; changes the cost/latency profile).

---

## 10. Module placement & reuse

| Piece | Home | Why |
|---|---|---|
| TUI API contract types, registry, execution center, loadout, explorer/tester | `cli/tui/tool_api/` | generic + reusable; aligns with dev's shared `cli/tui/` lib |
| Bedrock-specific glue (toolConfig builder, the engine tool loop, doc attachment) | `aws/bedrock/tui/` | provider-specific |
| Each host's TUI API provider + SKILL files | with the host (e.g. `sg_edge/.../tui_api/`, `aws/s3/.../tui_api/`) | co-located with the capability it exposes |

This keeps the chat a pure consumer and lets the **same** provider definition be driven
from the chat, the explorer, pytest, and the CLI — the JS pattern's "equal consumers"
invariant, on the Python side.

---

## 11. Slice plan

| Slice | Scope | Textual? |
|---|---|---|
| **A1 — contract + registry (pure)** | the Type_Safe schemas, JSON-Schema-from-Type_Safe, `Tui_Api__Provider` + `Registry`, `sg <area> tui-api list/manifest/skills`. One real provider (a read-only `sg aws s3` slice). Full unit tests, no Textual. | no |
| **A2 — execution center (pure)** | modes, schema-validation, privilege resolver (over scoped-creds), dry-run/simulate, `..._ALLOW_MUTATIONS` gate, audit ring buffer, `sg <area> tui-api invoke`. Unit-tested with in-memory providers. | no |
| **A3 — chat tool loop** | toolConfig from loadout, the Converse tool-use loop in the engine, toolResult, per-turn cost summing all sub-calls. Pilot + pure tests. | yes |
| **A4 — loadout UI** | the loadout modal + `--tools` flag; only granted actions/SKILLs reach the model. | yes |
| **A5 — Inspector extension** | render toolUse/toolResult + audit entries; transcript tool blocks. | yes |
| **A6 — Swagger-style explorer/tester** | the explorer/console screen + the automated contract-test harness. | yes |
| **D1 — documents** | Converse document attachments (picker + chip + cost) + N-doc persistent context. | yes |

Build order: A1→A2 are the valuable, framework-free core (and independently useful as
`sg ... tui-api` CLI). A3 makes the chat agentic. A4–A6 add control + visibility. D1 in parallel.

---

## 12. Acceptance criteria

| # | Criterion | Verification |
|---|---|---|
| 1 | A host exposes a TUI API discoverable from the CLI **and** read by the chat from the same source | `sg <area> tui-api manifest` == what the chat loads |
| 2 | Every action carries **real JSON Schema**; model output validates against it | contract test |
| 3 | Tiers + privileges are declared and **enforced** before execution | priv-miss refuses with the minimal policy |
| 4 | Loadout scopes what the model sees; over-tier actions are invisible, not just refused | pilot |
| 5 | WRITE+ actions preview (dry-run) and require confirm / `ALLOW_MUTATIONS`; nothing mutates silently | pilot + unit |
| 6 | Per-turn cost sums all model + tool round-trips; visible in meter + Inspector | pilot |
| 7 | The explorer drives the same registry/execution center as the chat; automated contract tests pass | pytest, no mocks |
| 8 | Documents attach to a turn / seed the session; added token cost is shown | pilot |

---

## 13. Open questions

| Question | Recommendation |
|---|---|
| Default exec mode per tier | AUTO for READ_ONLY, CONFIRM for WRITE/CRUD, CONFIRM-with-typed-confirm for DESTRUCTIVE. |
| Do browser (JS) tools ever need driving from the TUI? | Out of v1 (Python-native only). If yes later, add an HTTP/MCP bridge provider that satisfies the same contract. |
| JSON Schema source of truth for shared tools | Enrich the JS manifests to real JSON Schema (option b) so browser + TUI share one definition; Python tools derive from Type_Safe. |
| Privilege resolution depth | v1: presence/role check via scoped-creds + print-policy on miss. Live IAM simulation (`iam:SimulatePrincipalPolicy`) is a later enhancement. |
| Fractal depth | v1: one level of child providers, render the tree. |
| Should the chat be allowed to change its own loadout? | No — loadout is a human/host decision; the model requests capabilities it lacks via a normal answer, the human grants via the loadout. |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
