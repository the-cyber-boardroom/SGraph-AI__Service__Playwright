---
title: "TUI API — implementation plans (index + reuse map)"
file: 00__plans-index.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — for Dev pickup. Grounded in a code survey of what already exists (this session).
parent: ../01__tui-api-contract-and-conventions.md
---

# TUI API — implementation plans

The ratified standard ([`../01__tui-api-contract-and-conventions.md`](../01__tui-api-contract-and-conventions.md))
defines the data model and the 10 ratified decisions. These plans turn it into buildable
slices, each grounded in a survey of what the repo **already has** (so we build thin over
existing primitives, per the playbook).

## Reading order

| Plan | Slice | Build phase | Pure? |
|---|---|---|---|
| [`01__B1-contract-and-registry.md`](01__B1-contract-and-registry.md) | contract types + registry + `sg <area> tui api` CLI + schema-from-Type_Safe + first read-only S3 provider | B1 | yes (3.11) |
| [`02__B2-sg-role-and-privileges.md`](02__B2-sg-role-and-privileges.md) | SG/Role tokens + privilege resolver over `aws/creds` | B2 | yes (3.11) |
| [`03__B3-execution-center.md`](03__B3-execution-center.md) | modes, schema-validate, sequencing/preconditions, mutation gate, audit | B3 | yes (3.11) |
| [`04__B4-vfs-core-tool.md`](04__B4-vfs-core-tool.md) | `memory_fs`-backed VFS core tool + `/tools/<tool>/` conventions | B4 | yes (3.12-gated) |
| [`05__B5-explorer-and-C-chat-slices.md`](05__B5-explorer-and-C-chat-slices.md) | Swagger explorer/tester + the chat consumption slices (C-P0…D1) | B5 + C | mixed |
| [`06__core-tools-web-bash-python.md`](06__core-tools-web-bash-python.md) | **PROPOSED** — three more core tools: Web Access (READ_ONLY), Bash + Python (DESTRUCTIVE, ephemeral containers); needs a temp-folder VFS backend to share with containers | future | mixed |
| [`07__multi-backend-chat-reconciliation.md`](07__multi-backend-chat-reconciliation.md) | **PROPOSED** — the `Chat__Backend` seam (Bedrock/Ollama/OpenRouter) that preserves the built tools/documents/agentic loop; reconciles dev's multi-provider plan with this branch | future | n/a |

Build order: **B1 → B2 → B3 → B4** (each pure, independently testable, no Textual), then
**B5** + the **C** chat slices. B1 is the keystone and is shippable on its own as the
`sg <area> tui api` CLI.

---

## The reuse map (verified this session — file:line)

Everything below **EXISTS** and was read; the plans build over it rather than re-inventing.

### Schema emission (decision #9 — "derive programmatically")
- **`Type_Safe__Schema_For__LLMs.export(ParamsClass) -> dict`** — `osbot_utils/helpers/llms/actions/Type_Safe__Schema_For__LLMs.py`. Emits JSON Schema from a Type_Safe class: primitives, `List`/`Dict`/`Tuple`/`Set`, `Optional`/`Union`, **nested Type_Safe**, validators (`Min`/`Max`/`Regex`/`One_Of`→`enum`), and **descriptions pulled from inline `#` comments**. This is the `Action.input_schema` source — no hand-written JSON.
- **`Schema__LLM_Request__Function_Call`** (`parameters: Type[Type_Safe]`, `function_name`, `description`) — `osbot_utils/helpers/llms/schemas/`. The function-call shape; pairs with the emitter for the chat tool loop (C-TL1). (Only an OpenAI platform exists in osbot — the **Bedrock** `toolConfig` mapping is genuinely new, slice C-TL2.)

### The CLI tree (B1 wiring)
- Entry point: `sg = "sg_compute.cli.Cli__SG:app"` (Typer); aliases `sgc`/`sg-compute`/`sp` (`pyproject.toml`).
- Root `sg_compute/cli/Cli__SG.py` is a `typer.Typer` that `.add_typer(area_app, name=...)` for ~20 areas. Areas nest the same way: `aws` → `aws bedrock` → `aws bedrock chat`.
- **`tui` is registered as a leaf command** today: `register_tui(chat_app)` does `@app.command('tui')` (`aws/bedrock/tui/cli/Cli__Bedrock__Chat__Tui.py:84`). **To get `tui api`, `tui` must become a Typer sub-group** (`invoke_without_command=True` + a callback that launches the TUI). See B1 §CLI.
- **No cross-area registry exists** — explicit per-area registration is the house pattern and what B1 uses.
- Shared TUI lib already at **`sgraph_ai_service_playwright__cli/tui/`** (`components/Tui__App.py`, `debug/`). `tool_api/` lives here.

### The first provider (B1)
- **`S3__AWS__Client`** (Type_Safe) — `aws/s3/service/S3__AWS__Client.py`. Read-only: `list_buckets()`, `list_objects(bucket, prefix='', recursive=False)`, `head_object(bucket, key)`, `get_object_body`, `search_objects`. Returns Type_Safe schemas (`Schema__S3__Bucket`, `Schema__S3__List__Response`, `Schema__S3__Object`, `Schema__S3__Stat`).
- **`S3__AWS__Client__In_Memory(S3__AWS__Client)`** — `tests/.../aws/s3/service/S3__AWS__Client__In_Memory.py`; fluent `add_bucket()` / `add_object()`. The no-mock test double.
- Reusable input primitives: `Safe_Str__S3__Bucket`, `Safe_Str__S3__Key`, `Safe_Str__S3__Prefix`, `Safe_Str__AWS__Region`.

### The SG/Role substrate (B2 — richer than assumed)
- **`Schema__Creds__Scope`** (`name`, `role_arn`, `max_ttl`, `created_at`) — `aws/creds/schemas/`. A named scope = role ARN + TTL.
- **`Creds__Scope__Catalogue`** — JSON at `~/.sg/aws/creds/scopes.json` (0600); `scope_get/add/remove/list`. The persistence pattern to mirror for SG/Role grants.
- **`Schema__Creds__Assumption`** (`scope_name`, `role_arn`, `caller`, `assumed_at`, `expires_at`, `session_token`) + **`Creds__STS__Client`** + **`Creds__Audit__Log`** — STS assume-role with audit.
- **`Creds__TTL__Parser.parse('1h') -> seconds`** — the time-bounds (decision #2) already exist.
- So **SG/Role maps down to a creds scope**: capability `sg-aws.s3:read` → (for AWS) a `Schema__Creds__Scope` role assumption; the TTL + audit are reused verbatim.

### The VFS substrate (B4)
- **`memory_fs`** (PyPI, Python **3.12**) — `Storage_FS` interface + `Storage_FS__Memory` (default, ephemeral). CRUD verified this session. Backends `Local_Disk`/`Sqlite`/`Zip` for opt-in persistence.

### The pilot host (Phase C)
- The built **Bedrock chat** (`aws/bedrock/tui/`): `Bedrock__Chat__Engine.send_turn`, `Schema__Bedrock__Chat__Session` (the `state()` surface), the Inspector (`request_json`/`response_text`). Engine built via a `_engine_factory` seam (`Cli__Bedrock__Chat__Tui.py:17`) tests replace — reuse for headless provider tests.

---

## Conventions every plan obeys (CLAUDE.md)

- All classes extend `Type_Safe`; **zero raw primitives** as attributes; fixed sets are `Enum__*`; schemas are pure data (no methods); **one class per file**; empty `__init__.py`; 80-char `═══` headers (Python only); inline comments, no docstrings.
- **No mocks, no patches** — compose in-memory (the `S3__AWS__Client__In_Memory` / `_engine_factory` patterns).
- Pure layers run on **3.11** (always); Textual + `memory_fs` layers are **gated** (skip cleanly when absent). The 3.12 venv `/tmp/venv312` runs the `memory_fs` tests.
- Branch `dev`; agents open a PR, never push to `dev`.

## Runtime / test matrix

| Layer | Runtime | Test command (indicative) |
|---|---|---|
| B1–B3 contract/registry/exec-center (pure) | 3.11 | `pytest sgraph_ai_service_playwright__cli/tui/tool_api/tests` |
| B4 VFS (memory_fs) | 3.12 | `/tmp/venv312/bin/pytest …/tool_api/core/vfs/tests` |
| B5 + C (Textual) | 3.11 + textual | gated `@skipUnless(textual_importable)` pilot |

---

## Known coverage gaps (need a slice decision)

A coherence pass (2026-05-21) found two parts of the standard not yet assigned to a build slice:

1. **Orientation + change-control surfaces.** The standard §4.4/§4.5 define `Schema__Tui_Api__Tool`,
   `Schema__Tui_Api__Orientation`, `Schema__Tui_Api__Change`, `Enum__Tui_Api__Change_Kind`, and the CLI
   §5 lists `status` / `whatsnew` / `changelog`. B1's CLI ships only `list/describe/skills/state/invoke`;
   B4 ships the VFS *file* delivery (`skills.md` etc.) but not the live `status`/`orientation()` method or
   the `Change` records. **Recommendation: add a small `B6 — orientation + change-control` slice**
   (the `Schema__Tui_Api__Tool`/`Orientation`/`Change` classes + `orientation()` provider method +
   `status`/`whatsnew`/`changelog` CLI), pure on 3.11, after B4. Change-capture is recommended-not-enforced (§10 #5).
2. **Workflow assembler.** `Schema__Tui_Api__Workflow` + the workflow→loadout assembly (standard §4.6) is
   consumer-side and currently only implied by **C-TL2**. **Recommendation: build it in C-TL2** (it is the
   loadout's source of truth) — no separate slice needed; just make it explicit in C-TL2.

**Owner ruling (2026-05-21):** add **B6** for orientation + change-control (after B4);
build the workflow assembler **in C-TL2**. Separately, **tool/API granularity is left
organic** — prove the slug model (`sg-aws.s3`, etc.) across several tools/services and let
the right grain emerge, rather than fixing a convention now.

**Foundation status (2026-05-21) — the framework-free core is BUILT:**
- ✅ **B1** contract + registry + CLI + S3 provider (`sg aws s3 tui api …`).
- ✅ **B2** SG/Role tokens + privilege resolver over `aws/creds`.
- ✅ **B3** execution center (sequencing, mutation gate, audit, dry-run); `invoke` routes through it.
- ✅ **B4** VFS core tool over `memory_fs` (3.12-gated).
- ✅ **B5** contract-test harness **and** the Textual explorer screen (`sg <area> tui api explore`),
  built from Textual built-ins (Header/Footer/DataTable/Static) and pilot-tested headless via
  `App.run_test()` with the in-memory S3 provider — the same way the chat/edge/s3 TUIs are tested.
- ✅ **B6** orientation + change-control (`status` / `whatsnew` / `changelog`); `Schema__Tui_Api__Tool`
  multi-API aggregation deferred until multi-API tools exist (organic granularity).
- ✅ **C-P0** chat is a TUI API provider (state/actions; `sg aws bedrock chat tui api …`).
- ✅ **C-TL1** the agentic Converse tool-use loop (`send_turn_agentic`) + `Bedrock__Tool_Config__Builder`;
  tools execute through the execution center; per-turn cost sums model + tool sub-calls.
- ✅ **C-TL2a** loadout + workflow assembler (`from_tools`/`from_workflow`/`granted_actions`).
- ✅ **C-TL2b** `--tools` wired into the interactive chat: streaming for plain chat, the agentic
  loop when tools are active; the chat registers the VFS core tool; pilot-tested (3.12).
- ✅ **C-TL3** Inspector renders the per-turn tool calls (✓/✗ · name · input · result); turn carries `tool_log`.
- ✅ **C-D1** Converse document attachments (`Bedrock__Chat__Documents`: load/validate/content-block;
  send_turn/agentic accept `documents`); the functional core.
- ✅ **UI: loadout modal** (`ctrl+g`) — `Tui_Api__Loadout__Modal`; cycle tiers, Apply → activates the agentic path.
- ✅ **UI: document picker** (`ctrl+d`) + chip row — `Bedrock__Chat__Doc__Picker` + `Chat__Doc__Chips`.
- N-doc persistent context: covered — attached docs are stored on the user message and re-included
  by `build_messages` every turn, so they remain context for the rest of the session.

**EVERYTHING BUILT.** The TUI API standard (B1–B6) and the full Bedrock chat consumption
(C-P0/TL1/TL2/TL3/D1) + the UI (explorer, loadout modal, doc picker/chips, inspector tool
blocks) are complete end-to-end.

**Runtime:** the project targets **Python 3.12**. A single 3.12 interpreter runs the whole
suite (textual + memory_fs + boto3 together): **3.12 → 113 passed.** On a 3.11 lane the
memory_fs / agentic-pilot tests skip cleanly. All pushed to `claude/review-tui-cli-commits-S3xCM`.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
