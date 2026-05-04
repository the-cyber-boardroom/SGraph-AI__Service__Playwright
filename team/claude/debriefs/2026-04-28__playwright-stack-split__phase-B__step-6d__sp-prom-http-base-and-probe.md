# Phase B · Step 6d — `sp prom` HTTP base + probe

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B step 5d (`05c0bb7`) — `sp os` HTTP base + probe.
**Predecessor:** Phase B step 6c — `sp prom` AWS helpers (`6141cf3`).

---

## What shipped

Two small focused HTTP files, one class each, mirroring the OS pattern.

| File | Role |
|---|---|
| `prometheus/service/Prometheus__HTTP__Base.py` | Wraps `requests` with `verify=False` default + scoped urllib3 warning suppression + Basic auth seam. Adds a `params` kwarg (used by `/api/v1/query`). Tests substitute `requests.request` via a recorder. |
| `prometheus/service/Prometheus__HTTP__Probe.py` | 3 read-only probes: `prometheus_ready` (200 on `/-/healthy`), `targets_status` (parsed `/api/v1/targets`; `{}` on failure — caller derives counts from `data.activeTargets`), `query` (`/api/v1/query?query=…` for the future `sp prom query` command). |

## Departures from the `sp os` template

- **3 probes instead of 2.** OS only needed cluster_health + dashboards_ready. Prom adds `query()` so the future `sp prom query` typer command (deferred per plan 5) can compose this directly without a new HTTP file.
- **`params` kwarg in HTTP base.** `/api/v1/query` takes the PromQL string as a query-string param, not a path component. Adding it once in the base means the probe stays small.
- **`verify=False` kept for parity.** Today Prometheus serves plain HTTP on 9090 — `verify=False` is harmless on `http://` URLs but the seam stays identical to OS in case a future nginx-fronted variant lands.
- **No mandatory auth** — Basic auth params still optional (P1: Prometheus has no built-in auth) but the seam is there for nginx-wrapped deployments.

## Tests

16 new tests, all green:

| Group | Tests |
|---|---|
| `Prometheus__HTTP__Base` | 5 — defaults, verify=False + default timeout + auth=None, basic auth attached, custom timeout, params forwarded |
| `prometheus_ready` (probe) | 4 — 2xx (multiple codes), non-2xx, network error → False, trailing-slash hygiene |
| `targets_status` (probe) | 4 — 200 returns parsed body, non-200 → {}, network → {}, non-JSON → {} |
| `query` (probe) | 3 — forwards `?query=…` param, non-200 → {}, network → {} |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 65 | 81 | +16 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__HTTP__Base.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__HTTP__Probe.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__HTTP__Base.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__HTTP__Probe.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 6e — `Prometheus__Service` orchestrator (read paths) + `Caller__IP__Detector` + `Random__Stack__Name__Generator` + `Stack__Mapper`.
