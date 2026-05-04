# Phase B · Step 7a — `sp vnc` foundation

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6a (`1a19d3f`) — `sp prom` foundation.
**Predecessor:** Phase B step 6h — `sp prom` complete (`c81a1b1`).

---

## What shipped

First slice of the new browser-viewer sister section. Same shape as the prior 6a / 5a foundations — folder + naming-shape primitives + lifecycle enum + AWS-client skeleton with tag constants.

| File | Role |
|---|---|
| `cli/vnc/__init__.py` | Empty package marker |
| `cli/vnc/primitives/Safe_Str__Vnc__Stack__Name.py` | Stack name primitive — regex parity with elastic + os + prom locked by test |
| `cli/vnc/primitives/Safe_Str__IP__Address.py` | Local copy (sister sections stay self-contained) |
| `cli/vnc/primitives/Safe_Str__Vnc__Password.py` | Operator password (URL-safe base64, 16-64 chars). One password used for **both** nginx Basic auth and `MITM_PROXYAUTH` on the mitmproxy container — service generates once and uses twice |
| `cli/vnc/enums/Enum__Vnc__Stack__State.py` | Lifecycle vocabulary; shape parity locked by test |
| `cli/vnc/service/Vnc__AWS__Client.py` | Skeleton: `VNC_NAMING = Stack__Naming(section_prefix='vnc')` + 7 tag constants (`sg:purpose=vnc`, `sg:section=vnc`, plus `sg:interceptor` per N5) + `TAG_INTERCEPTOR_NONE='none'` constant |

## Naming choice

Folder `vnc/` (no long form / short alias split — per plan doc 6 N1, the section is `sp vnc` only; `sp nvm` was the working title and was dropped). Typer command will be `sp vnc` only.

## Departures from the `sp prom` 6a template

- **One password primitive.** sp prom had no password (no built-in auth in Prom). sp vnc reuses one password for two boundaries (nginx + mitmproxy proxy auth) — same regex shape as `Safe_Str__OS__Password`.
- **`sg:interceptor` tag** in the constants block, ready for the Tags__Builder (7c) to set per N5: `'none'` (default-off), `'name:<example>'` (baked example loaded by name), `'inline'` (raw Python source baked at create time).

## Tests

24 new tests:

| Group | Tests |
|---|---|
| `Safe_Str__Vnc__Stack__Name` | 6 — valid names, lowercases, rejects start-with-digit / underscore, empty allowed, regex parity with elastic + os + prom |
| `Safe_Str__Vnc__Password` | 4 — valid forms, rejects too-short, rejects non-URL-safe chars, empty allowed |
| `Enum__Vnc__Stack__State` | 4 — exhaustive set, lowercase values, `__str__`, shape parity |
| `VNC_NAMING` | 5 — Stack__Naming instance, prefix correct, aws_name_for_stack adds/never-doubles, sg_name_for_stack appends `-sg` |
| Tag constants | 4 — purpose value, section value, interceptor constants, all `sg:`-namespaced |
| Skeleton | 1 — instantiates cleanly |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 0 | 24 | +24 |

## What was deferred

- 7b — schemas + collections (incl. `Schema__Vnc__Interceptor__Choice` per N5)
- 7c — AWS helpers (SG / AMI / Instance / Tags / Launch). SG ports: 443 nginx + 3000 KasmVNC SSM-only + 8080 mitmproxy proxy
- 7d — HTTP probe — nginx 200 + mitmweb `/api/flows` reachable
- 7e — `Vnc__Service` orchestrator
- 7f — user-data + compose (3 containers: chromium + nginx + mitmproxy) + interceptor resolution + create_stack
- 7g — `Routes__Vnc__Stack` + `Routes__Vnc__Flows`
- 7h — `scripts/vnc.py` typer

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/primitives/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/primitives/Safe_Str__Vnc__Stack__Name.py
A  sgraph_ai_service_playwright__cli/vnc/primitives/Safe_Str__IP__Address.py
A  sgraph_ai_service_playwright__cli/vnc/primitives/Safe_Str__Vnc__Password.py
A  sgraph_ai_service_playwright__cli/vnc/enums/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/enums/Enum__Vnc__Stack__State.py
A  sgraph_ai_service_playwright__cli/vnc/service/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__AWS__Client.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/primitives/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/primitives/test_Safe_Str__Vnc__Stack__Name.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/primitives/test_Safe_Str__Vnc__Password.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/enums/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/enums/test_Enum__Vnc__Stack__State.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 7b — schemas + collections. Includes `Schema__Vnc__Interceptor__Choice` (the N5 selector — none / name / inline-source).
