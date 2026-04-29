# `sp vnc` — Handover dev-pack

**Date stamped:** 2026-04-29.
**Status of `sp vnc`:** functionally complete in pure logic + typer (Tier-2A); FastAPI routes built and tested (Tier-2B) but **not yet wired to `Fast_API__SP__CLI`**.

This pack hands off the `sp vnc` sister section to a fresh agent session. Read in numerical order:

| # | Doc | What it covers |
|---|---|---|
| 00 | this file | Entry point + reading order |
| 01 | [`01__cli-tier-2a.md`](./01__cli-tier-2a.md) | Typer commands — `sp vnc {create, list, info, delete, health, flows, interceptors}` |
| 02 | [`02__code-tier-1.md`](./02__code-tier-1.md) | `cli/vnc/` folder structure — services, schemas, primitives, enums |
| 03 | [`03__api-tier-2b.md`](./03__api-tier-2b.md) | FastAPI routes — `Routes__Vnc__Stack` + `Routes__Vnc__Flows`. **Not yet wired to Fast_API__SP__CLI.** |
| 04 | [`04__missing-wiring.md`](./04__missing-wiring.md) | The gap — exactly what to add to `Fast_API__SP__CLI` to mount the VNC routes (VNC-only scope) |
| 05 | [`05__catalog-integration.md`](./05__catalog-integration.md) | `Enum__Stack__Type.VNC` exists; `Stack__Catalog__Service` does NOT compose `Vnc__Service` yet |
| 06 | [`06__broader-fast-api-context.md`](./06__broader-fast-api-context.md) | Appendix — same wiring gap exists for `sp os` / `sp prom`. Out of scope for the next session, but captured so it isn't lost. |

## Top-line summary

**What works today:**
- `sp vnc create [name] [--interceptor <name> | --interceptor-script <path>]` — provisions a chromium + nginx + mitmproxy EC2 stack
- `sp vnc list / info / delete / health / flows / interceptors`
- Same operations exist as `Vnc__Service.{create_stack, list_stacks, get_stack_info, delete_stack, health, flows}`
- 189 unit tests, all green; real `_Fake_*` subclasses, no mocks

**What's NOT wired:**
- `POST /vnc/stack` etc. — route classes built and tested via FastAPI TestClient, but `Fast_API__SP__CLI.setup_routes()` doesn't mount them
- `Stack__Catalog__Service.list_all_stacks()` doesn't enumerate VNC stacks (catalog enum lists VNC, but the service composition skips it)

**Implementation pattern (read first if unfamiliar):**
- Each sister section follows: `primitives/` → `enums/` → `schemas/` → `collections/` → `service/` (Tier-1) → `fast_api/routes/` (Tier-2B) → `cli/Renderers.py` + `scripts/<section>.py` (Tier-2A)
- Same shape used by `sp os`, `sp prom`, `sp linux`, `sp docker`, `sp el`. Use those as references.
- Type_Safe everywhere; no Pydantic; no mocks; one class per file.

## Plan reference

`team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md` — sign-offs N1 / N2 / N3 / N4 / N5.

## Recent shipping commits (this branch)

| Commit | Slice |
|---|---|
| `4c7b1b7` | 7a — foundation |
| `3e6803b` | 7b — schemas + collections (incl. N5 `Schema__Vnc__Interceptor__Choice`) |
| `7ae5ad2` | 7c — AWS helpers (4 small files; SG port 443) |
| `4d5a035` | 7d — HTTP base + probe (nginx + mitmweb + flows-listing) |
| `877791e` | 7e — Service orchestrator (read paths) + flows() |
| `fc5f5fc` | 7f — user-data + compose + interceptor resolver + launch + wire `create_stack` |
| `2eb7bb7` | 7g — FastAPI routes (Stack + Flows) |
| `41120fc` | 7h — typer commands + Renderers + mount on `sp` |

Per-slice debriefs at `team/claude/debriefs/2026-04-29__playwright-stack-split__phase-B__step-7{a..h}__*.md`.
