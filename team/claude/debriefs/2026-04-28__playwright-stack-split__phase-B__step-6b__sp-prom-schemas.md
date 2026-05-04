# Phase B · Step 6b — `sp prom` schemas + collections

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B step 5b (`9a1e04e`) — `sp os` schemas.
**Predecessor:** Phase B step 6a — `sp prom` foundation (`1a19d3f`).

---

## What shipped

7 schemas + 2 collections for the Prometheus sister section. Mirrors the `sp os` 5b shape minus password / Dashboards URL fields (P1: no Grafana, no built-in auth) and plus the `Schema__Prom__Scrape__Target` (P3: one-shot baked targets baked into prometheus.yml at create time).

| File | Role |
|---|---|
| `cli/prometheus/schemas/Schema__Prom__Scrape__Target.py` | One scrape job baked into prometheus.yml. `job_name` + `targets` (host:port list) + `scheme` (http/https) + `metrics_path` (/metrics by default). |
| `cli/prometheus/schemas/Schema__Prom__Stack__Create__Request.py` | Inputs for `sp prom create [NAME]`. All fields optional. Includes `scrape_targets : List__Schema__Prom__Scrape__Target` for the baked target list. **No** `admin_password` (Prometheus has no built-in auth — P1). |
| `cli/prometheus/schemas/Schema__Prom__Stack__Create__Response.py` | Returned once on create. **No** `admin_password` / `admin_username` / `dashboards_url` (P1). Carries `prometheus_url` (http://&lt;ip&gt;:9090/) and `targets_count`. |
| `cli/prometheus/schemas/Schema__Prom__Stack__Info.py` | Public view of one stack. **No** password field; defensive test asserts no `password` in any annotation. |
| `cli/prometheus/schemas/Schema__Prom__Stack__List.py` | Response wrapper — `region` + `stacks : List__Schema__Prom__Stack__Info`. |
| `cli/prometheus/schemas/Schema__Prom__Stack__Delete__Response.py` | Empty fields ⇒ caller maps to HTTP 404. Carries `terminated_instance_ids : List__Instance__Id` (reused from `cli/ec2/`). |
| `cli/prometheus/schemas/Schema__Prom__Health.py` | Health snapshot — `prometheus_ok` (True iff `/-/healthy` returns 200), `targets_total` / `targets_up` (-1 sentinels = unreachable). |
| `cli/prometheus/collections/List__Schema__Prom__Stack__Info.py` | Pure type definition — listing collection. |
| `cli/prometheus/collections/List__Schema__Prom__Scrape__Target.py` | Pure type definition — ordered list of scrape jobs. |
| `cli/prometheus/collections/List__Str.py` | Local typed list of plain strings (host:port targets). Section-local copy — sister sections stay self-contained. |

## Departures from the `sp os` template

- **No `Safe_Str__Prom__Password` primitive.** Prometheus exposes a public HTTP API with no built-in auth (P1: Grafana / dashboards live elsewhere). Defensive tests on Request / Response / Info iterate `__annotations__` and assert `'password' not in field.lower()` so no future drift introduces one quietly.
- **No `dashboards_url` field.** Same reason — no UI in this stack.
- **`metrics_path : Safe_Str__Url__Path` not `Safe_Str__Text`.** First test run caught `Safe_Str__Text` stripping `/` from `/metrics` → `_metrics`. `Safe_Str__Url__Path` preserves slashes (regex `^/?[a-zA-Z0-9/\-._~%]*$`).
- **`scheme : Safe_Str__Id` not `Safe_Str__Text`.** Schemes are alphanumeric (`http` / `https`); `Safe_Str__Id` is the right shape. Tests round-trip both values.

## Tests

23 new tests, all green:

| Group | Tests |
|---|---|
| `Schema__Prom__Scrape__Target` | 2 — defaults (`/metrics`, `http`, empty targets), JSON round-trip with `https` + 2 host:port + `/api/metrics` (slash preserved) |
| `Schema__Prom__Stack__Create__Request` | 3 — defaults, **no-password defensive** check, JSON round-trip with one scrape target |
| `Schema__Prom__Stack__Create__Response` | 3 — defaults (`PENDING`, `targets_count=0`), no-password defensive, JSON round-trip with `prometheus_url` |
| `Schema__Prom__Stack__Info` | 3 — defaults, JSON round-trip, no-password defensive |
| `Schema__Prom__Stack__List` + `Delete__Response` | 4 — defaults / round-trip for both wrappers (region empty, two-stack listing; empty-on-miss + populated terminated ids) |
| `Schema__Prom__Health` | 2 — defaults are `-1` sentinels + `prometheus_ok=False`, round-trip with state/targets populated |
| `List__Schema__Prom__Stack__Info` | 3 — `expected_type` locked, append + iterate, rejects wrong type |
| `List__Schema__Prom__Scrape__Target` | 3 — same shape |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 19 | 42 | +23 |

Pre-existing failures unrelated to this work — the same 8 in `lets/cf/` (1 `S3__Inventory__Lister` flake noted in the v0.1.96 handover; 7 `SG_Send__Orchestrator` cases active on the observability branch).

## Bug surfaced + fixed

- `Safe_Str__Text` strips slashes — first test run reported `/metrics` → `_metrics` and `/api/metrics` → `_api_metrics`. Fixed by switching `metrics_path` to `Safe_Str__Url__Path`. The bug would have rendered an unusable prometheus.yml when 6f wires the compose template, so catching it at the schema layer kept the cost local.

## What was deferred

- 6c — AWS helpers (SG / AMI / Instance / Tags / Launch). SG ingress port 9090.
- 6d — `Prometheus__HTTP__Base` + `Prometheus__HTTP__Probe` (`/-/healthy`, `/api/v1/targets`, `/api/v1/query` for the future `sp prom query` command).
- 6e — `Prometheus__Service` orchestrator with `setup()` lazy-init.
- 6f — user-data + compose (3 services: prometheus + cadvisor + node-exporter; baked prometheus.yml from `Schema__Prom__Scrape__Target` list per P3).
- 6g — `Routes__Prometheus__Stack` (5 routes mirroring `Routes__OpenSearch__Stack`).
- 6h — `scripts/prometheus.py` typer app + Renderers, mounted via `add_typer` with `sp prom` short alias.

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/collections/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/collections/List__Str.py
A  sgraph_ai_service_playwright__cli/prometheus/collections/List__Schema__Prom__Scrape__Target.py
A  sgraph_ai_service_playwright__cli/prometheus/collections/List__Schema__Prom__Stack__Info.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Scrape__Target.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Stack__Create__Request.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Stack__Create__Response.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Stack__Info.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Stack__List.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Stack__Delete__Response.py
A  sgraph_ai_service_playwright__cli/prometheus/schemas/Schema__Prom__Health.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/collections/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/collections/test_List__Schema__Prom__Scrape__Target.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/collections/test_List__Schema__Prom__Stack__Info.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/test_Schema__Prom__Scrape__Target.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/test_Schema__Prom__Stack__Create__Request.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/test_Schema__Prom__Stack__Create__Response.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/test_Schema__Prom__Stack__Info.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/test_Schema__Prom__Stack__List_and_Delete.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/schemas/test_Schema__Prom__Health.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Failure classification

**Good failure** — `Safe_Str__Text` slash-stripping caught immediately at schema-test time. Locked the right primitive (`Safe_Str__Url__Path`) before any prometheus.yml renderer is written in 6f.

## Next

Step 6c — 4 small AWS helpers (SG / AMI / Instance / Tags) + Launch helper. SG ingress port 9090 only (per plan 5: no Grafana 3000, no Loki 3100).
