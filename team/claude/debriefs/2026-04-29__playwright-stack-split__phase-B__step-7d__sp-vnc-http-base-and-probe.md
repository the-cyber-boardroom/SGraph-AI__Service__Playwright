# Phase B · Step 7d — `sp vnc` HTTP base + probe

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6d (`23f82f8`) — `sp prom` HTTP base + probe.
**Predecessor:** Phase B step 7c — `sp vnc` AWS helpers (`7ae5ad2`).

---

## What shipped

| File | Role |
|---|---|
| `vnc/service/Vnc__HTTP__Base.py` | `requests` wrapper with `verify=False` (nginx self-signed cert at boot) + Basic auth seam + `params` kwarg for parity with the prom shape. |
| `vnc/service/Vnc__HTTP__Probe.py` | 3 read-only probes: `nginx_ready` (200 on `/`), `mitmweb_ready` (200 on `/api/flows`), `flows_listing` (parsed JSON list from `/api/flows`; `[]` on any failure). |

## Departures from the `sp prom` 6d template

- **3 probes, different shape**: nginx-front + mitmweb-reachability + flows-listing (vs prom's healthy/targets/query). The `flows_listing` probe is consumed by `Routes__Vnc__Flows` in 7g.
- **Defensive non-array body check** — `flows_listing` returns `[]` if mitmweb ever changes to return `{'flows': […]}` or any non-list shape, so the route handler never trips on type errors.

## Tests

15 new tests, all green:

| Group | Tests |
|---|---|
| `Vnc__HTTP__Base` | 3 — defaults, verify=False + default timeout, Basic auth attached |
| `nginx_ready` | 4 — 2xx ready, non-2xx not ready, network → False, trailing-slash hygiene |
| `mitmweb_ready` | 3 — 200 only is ready, non-200 → False, network → False |
| `flows_listing` | 5 — 200 returns parsed list, non-200 → [], non-JSON → [], non-array body → [], network → [] |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 74 | 89 | +15 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__HTTP__Base.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__HTTP__Probe.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__HTTP__Base.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__HTTP__Probe.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 7e — `Vnc__Service` orchestrator (read paths) + `Caller__IP__Detector` + `Random__Stack__Name__Generator` + `Vnc__Stack__Mapper`.
