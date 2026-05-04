# `sp vnc` — Handover dev-pack

**Date stamped:** 2026-04-29.
**Updated:** 2026-04-29 — wiring complete (see below).
**Status of `sp vnc`:** ✅ **SHIPPED** — all tiers wired. Routes live on the deployed FastAPI service. VNC stacks appear in `GET /catalog/stacks`.

This pack hands off the `sp vnc` sister section to a fresh agent session. Read in numerical order:

| # | Doc | What it covers |
|---|---|---|
| 00 | this file | Entry point + reading order |
| 01 | [`01__cli-tier-2a.md`](./01__cli-tier-2a.md) | Typer commands — `sp vnc {create, list, info, delete, health, flows, interceptors}` |
| 02 | [`02__code-tier-1.md`](./02__code-tier-1.md) | `cli/vnc/` folder structure — services, schemas, primitives, enums |
| 03 | [`03__api-tier-2b.md`](./03__api-tier-2b.md) | FastAPI routes — `Routes__Vnc__Stack` + `Routes__Vnc__Flows`. ✅ Wired to `Fast_API__SP__CLI`. |
| 04 | [`04__missing-wiring.md`](./04__missing-wiring.md) | ✅ DONE — `Fast_API__SP__CLI` now mounts VNC routes; `vnc_service.setup()` called; catalog shares instance |
| 05 | [`05__catalog-integration.md`](./05__catalog-integration.md) | ✅ DONE — `Stack__Catalog__Service` now composes `Vnc__Service`; `list_all_stacks` enumerates VNC stacks |
| 06 | [`06__broader-fast-api-context.md`](./06__broader-fast-api-context.md) | Appendix — same wiring gap exists for `sp os` / `sp prom`. Out of scope for the next session, but captured so it isn't lost. |

## Top-line summary

**What works today:**
- `sp vnc create [name] [--interceptor <name> | --interceptor-script <path>]` — provisions a chromium + nginx + mitmproxy EC2 stack
- `sp vnc list / info / delete / health / flows / interceptors`
- Same operations exist as `Vnc__Service.{create_stack, list_stacks, get_stack_info, delete_stack, health, flows}`
- 189 unit tests, all green; real `_Fake_*` subclasses, no mocks

**What was NOT wired (now fixed 2026-04-29):**
- ~~`POST /vnc/stack` etc. — route classes built and tested via FastAPI TestClient, but `Fast_API__SP__CLI.setup_routes()` doesn't mount them~~
- ~~`Stack__Catalog__Service.list_all_stacks()` doesn't enumerate VNC stacks~~

**Current state — fully wired:**
- `Routes__Vnc__Stack` + `Routes__Vnc__Flows` mounted in `Fast_API__SP__CLI.setup_routes()`
- `vnc_service.setup()` called in `Fast_API__SP__CLI.setup()` before route handling
- `catalog_service.vnc_service` shares the initialised instance (avoids double-init)
- `Stack__Catalog__Service` has `vnc_service: Vnc__Service` field + VNC branch in `list_all_stacks`
- Two new tests in `test_Fast_API__SP__CLI.py`: `test_vnc_routes_are_mounted` + `test_vnc_service_is_wired`

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
