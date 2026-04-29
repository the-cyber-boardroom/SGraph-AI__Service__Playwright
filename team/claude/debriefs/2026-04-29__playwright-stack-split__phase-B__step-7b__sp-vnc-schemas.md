# Phase B · Step 7b — `sp vnc` schemas + collections

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6b (`a1c814c`) — `sp prom` schemas.
**Predecessor:** Phase B step 7a — `sp vnc` foundation (`4c7b1b7`).

---

## What shipped

7 schemas + 2 collections + 1 new primitive + 1 new enum.

| File | Role |
|---|---|
| `vnc/primitives/Safe_Str__Vnc__Interceptor__Source.py` | Raw Python source for inline interceptors. Permissive regex (tabs + newlines + printable ASCII); `max_length=32 KB`; `trim_whitespace=False` so indentation survives. |
| `vnc/enums/Enum__Vnc__Interceptor__Kind.py` | N5 selector — `NONE` (default), `NAME`, `INLINE`. |
| `vnc/schemas/Schema__Vnc__Interceptor__Choice.py` | The N5 choice itself: `kind` + `name` (when NAME) + `inline_source` (when INLINE). |
| `vnc/schemas/Schema__Vnc__Stack__Create__Request.py` | Carries `operator_password` + `interceptor` choice. Defaults: max_hours=1, interceptor.kind=NONE. |
| `vnc/schemas/Schema__Vnc__Stack__Create__Response.py` | Carries `viewer_url`, `mitmweb_url`, `operator_password` (returned once), `interceptor_kind` + `interceptor_name`. |
| `vnc/schemas/Schema__Vnc__Stack__Info.py` | Public view — no password field (locked by defensive test). |
| `vnc/schemas/Schema__Vnc__Stack__List.py` | `region` + `stacks` wrapper. |
| `vnc/schemas/Schema__Vnc__Stack__Delete__Response.py` | Empty fields ⇒ HTTP 404. |
| `vnc/schemas/Schema__Vnc__Health.py` | `nginx_ok` + `mitmweb_ok` + `flow_count` (`-1` sentinel = unreachable). |
| `vnc/schemas/Schema__Vnc__Mitm__Flow__Summary.py` | One-line summary surfaced by `Routes__Vnc__Flows`. |
| `vnc/collections/List__Schema__Vnc__Stack__Info.py` | Listing collection. |
| `vnc/collections/List__Schema__Vnc__Mitm__Flow__Summary.py` | Flows collection. |

## Departures from the `sp prom` 6b template

- **Two new ancillary types**: `Schema__Vnc__Mitm__Flow__Summary` + its collection — for the `/v1/vnc/stack/{name}/flows` route landing in 7g.
- **One operator_password, used twice** in the user-data: nginx `htpasswd` + mitmproxy `MITM_PROXYAUTH`. The schema only knows about the one field; the user-data builder wires it into both places at render time.
- **Three-shape Interceptor__Choice** (N5): the route handler / typer accepts a partial body and the service composes the three valid combinations (NONE / NAME+name / INLINE+source). Defensive test exercises all three.
- **Custom `Safe_Str__Vnc__Interceptor__Source`** primitive — `osbot-utils.Safe_Str__Code__Snippet` exists but caps at 1024 chars (too small for typical mitmproxy interceptors). The new primitive permits 32 KB and preserves leading whitespace for indentation.

## Tests

24 new tests, all green:

| Group | Tests |
|---|---|
| `Schema__Vnc__Interceptor__Choice` | 4 — defaults to NONE / NAME shape / INLINE preserves Python source incl. indentation / round-trip |
| `Schema__Vnc__Stack__Create__Request` | 2 — defaults (interceptor.kind=NONE), round-trip with NAME interceptor |
| `Schema__Vnc__Stack__Create__Response` | 2 — defaults, round-trip with viewer/mitmweb URLs + NAME interceptor |
| `Schema__Vnc__Stack__Info` | 3 — defaults, round-trip, **no password** defensive |
| `Schema__Vnc__Stack__List` + `Delete__Response` | 4 — defaults / round-trip for both wrappers |
| `Schema__Vnc__Health` | 2 — sentinel defaults, round-trip |
| `Schema__Vnc__Mitm__Flow__Summary` (+ List) | 4 — defaults, round-trip, expected_type, append/iter |
| `List__Schema__Vnc__Stack__Info` | 3 — expected_type, append/iter, rejects wrong type |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 24 | 48 | +24 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/primitives/Safe_Str__Vnc__Interceptor__Source.py
A  sgraph_ai_service_playwright__cli/vnc/enums/Enum__Vnc__Interceptor__Kind.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Interceptor__Choice.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Mitm__Flow__Summary.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Stack__Create__Request.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Stack__Create__Response.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Stack__Info.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Stack__List.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Stack__Delete__Response.py
A  sgraph_ai_service_playwright__cli/vnc/schemas/Schema__Vnc__Health.py
A  sgraph_ai_service_playwright__cli/vnc/collections/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/collections/List__Schema__Vnc__Stack__Info.py
A  sgraph_ai_service_playwright__cli/vnc/collections/List__Schema__Vnc__Mitm__Flow__Summary.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Interceptor__Choice.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Mitm__Flow__Summary.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Stack__Create__Request.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Stack__Create__Response.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Stack__Info.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Stack__List_and_Delete.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/schemas/test_Schema__Vnc__Health.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/collections/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/collections/test_List__Schema__Vnc__Stack__Info.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 7c — 4 small AWS helpers (SG/AMI/Instance/Tags). SG ingress on port **443** (nginx TLS + viewer + proxied mitmweb). Per plan doc 6: KasmVNC port 3000 stays SSM-only (not in SG). The mitmproxy proxy port 8080 is SG-restricted and only the chromium container uses it (loopback on docker network) — including it in SG is operator's call.
