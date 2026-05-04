# Phase B · Step 7c — `sp vnc` AWS helpers (small-file discipline)

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6c (`6141cf3`) — `sp prom` AWS helpers.
**Predecessor:** Phase B step 7b — `sp vnc` schemas (`3e6803b`).

---

## What shipped

4 small focused AWS helpers + composition wired into `Vnc__AWS__Client.setup()`.

| File | Role |
|---|---|
| `vnc/service/Vnc__SG__Helper.py` | Port **443** (nginx TLS — chromium-VNC + proxied mitmweb). Idempotent. |
| `vnc/service/Vnc__AMI__Helper.py` | `latest_al2023` + `latest_healthy` filtered by `sg:purpose=vnc`. |
| `vnc/service/Vnc__Instance__Helper.py` | `list_stacks` / `find_by_stack_name` / `terminate_instance`. |
| `vnc/service/Vnc__Tags__Builder.py` | 7-tag list — adds `sg:interceptor` with N5 values (`'none'` / `'name:{ex}'` / `'inline'`). |
| `vnc/service/Vnc__AWS__Client.py` (modified) | Skeleton becomes composition shell — `sg`/`ami`/`instance`/`tags` slots wired by `setup()`. Launch helper joins in 7f. |

## Departures from the `sp prom` 6c template

- **Port 443, not 9090.** nginx TLS terminates at 443; KasmVNC stays SSM-only on 3000 (not in SG); mitmproxy 8080 is loopback-only.
- **7-tag list, not 6.** New `sg:interceptor` tag carries the N5 selector (`'none'` / `'name:<example>'` / `'inline'`). Inline source itself never appears in a tag — only the marker.
- **Tags__Builder takes a `Schema__Vnc__Interceptor__Choice`** (optional kwarg). When omitted, defaults to NONE → `'none'` tag value. Three shape tests lock the mapping.

## Tests

26 new tests, all green:

| Group | Tests |
|---|---|
| `Vnc__AWS__Client` | +2 (extended in-place from 1 to 3) — instantiates with all 4 slots None; setup() wires them; setup() returns self |
| `Vnc__SG__Helper` | 7 — port 443 constant, create-when-missing, reuse existing, duplicate-ingress swallowed, other ingress errors propagate, delete success, delete failure → False |
| `Vnc__AMI__Helper` | 4 — latest_al2023 returns most recent + filter shape, raises when none, latest_healthy filter shape (`sg:purpose=vnc`), empty when none |
| `Vnc__Instance__Helper` | 6 — list_stacks filters + key shape, skips no-id, find_by_stack_name hit + miss, terminate success + failure → False |
| `Vnc__Tags__Builder` | 7 — Name carries `vnc-` prefix, never doubles, full tag set, empty creator → `'unknown'`, **interceptor default = 'none'**, **NAME → `'name:header_logger'`**, **INLINE → `'inline'`** (source never tagged) |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 48 | 74 | +26 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__SG__Helper.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__AMI__Helper.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Instance__Helper.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Tags__Builder.py
M  sgraph_ai_service_playwright__cli/vnc/service/Vnc__AWS__Client.py
M  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__AWS__Client.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__SG__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__AMI__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Instance__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Tags__Builder.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 7d — `Vnc__HTTP__Base` + `Vnc__HTTP__Probe`. Probes: `nginx_ready` (200 on `/`), `mitmweb_ready` (`/api/flows` reachable), `flows_listing` (parsed `/api/flows` for the future `sp vnc flows` command).
