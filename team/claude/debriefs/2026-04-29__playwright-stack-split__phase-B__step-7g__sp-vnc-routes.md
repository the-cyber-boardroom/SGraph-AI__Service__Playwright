# Phase B · Step 7g — `sp vnc` FastAPI routes (Tier-2B)

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6g (`e4723ea`) — `sp prom` FastAPI routes.
**Predecessor:** Phase B step 7f — `sp vnc` create_stack wired (`fc5f5fc`).

---

## What shipped

Two route files. `Stack` mirrors prom; `Flows` is a per-stack peek into the mitmweb flow list (per N4 there is no auto-export).

| File | Role |
|---|---|
| `vnc/fast_api/routes/Routes__Vnc__Stack.py` | 5 routes under `/vnc`: `POST /stack`, `GET /stacks`, `GET/DELETE /stack/{name}` (404 on miss), `GET /stack/{name}/health`. `create` takes `body: dict` + round-trips via `Schema__Vnc__Stack__Create__Request.from_json(body)` (nested `Schema__Vnc__Interceptor__Choice` defeats pydantic auto-schema). |
| `vnc/fast_api/routes/Routes__Vnc__Flows.py` | One route — `GET /vnc/stack/{name}/flows` returns `{"flows": [...]}`. 404 when the stack doesn't exist; otherwise envelope with the (possibly empty) list of `Schema__Vnc__Mitm__Flow__Summary`. |

## Departure from the prom 6g template

- **Two route files, not one.** Stack lifecycle stays in `Routes__Vnc__Stack`; the flow listing has its own file because it's a different responsibility (mitmproxy interaction) and could grow more endpoints later (clear-flows, single-flow detail).
- **`create` body workaround** — same as prom: `Schema__Vnc__Stack__Create__Request` carries a nested `Schema__Vnc__Interceptor__Choice`, so FastAPI/pydantic can't auto-generate a body schema. `body: dict` + `from_json` keeps validation intact.
- **Flows envelope, not bare array** — `{"flows": [...]}` keeps the response future-proof (could add `total` / `dropped` later without breaking clients).

## Tests

13 new tests, all green:

| Group | Tests |
|---|---|
| `Routes__Vnc__Stack` — list / info | 4 — non-empty, empty, info hit (viewer + mitmweb URLs), info miss → 404 |
| `Routes__Vnc__Stack` — create | 2 — minimal body, **with NAME interceptor** (nested choice round-trips through `from_json`) |
| `Routes__Vnc__Stack` — delete | 2 — hit returns terminated ids, miss → 404 |
| `Routes__Vnc__Stack` — health | 1 — query-string creds forward; nginx + mitmweb flags + flow_count flow back |
| `Routes__Vnc__Flows` | 4 — miss → 404, hit empty, hit with 2 summaries, query-string creds forward |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 161 | 174 | +13 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/fast_api/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/fast_api/routes/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/fast_api/routes/Routes__Vnc__Stack.py
A  sgraph_ai_service_playwright__cli/vnc/fast_api/routes/Routes__Vnc__Flows.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/fast_api/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/fast_api/routes/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/fast_api/routes/test_Routes__Vnc__Stack.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/fast_api/routes/test_Routes__Vnc__Flows.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 7h — `scripts/vnc.py` typer + Renderers, mounted on the main `sp` app via `add_typer` as `sp vnc` (single name; no short alias per N1). Plus `sp vnc interceptors` to list the baked example names.
