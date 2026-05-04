# Phase B · Step 6c — `sp prom` AWS helpers (small-file discipline)

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B step 5c (`f5dcde7`) — `sp os` AWS helpers.
**Predecessor:** Phase B step 6b — `sp prom` schemas + collections (`a1c814c`).

---

## What shipped

4 small focused AWS helpers + wired composition into `Prometheus__AWS__Client.setup()`. Mirrors the `sp os` 5c split exactly, with one section-specific delta: SG ingress on **port 9090** (Prometheus' own UI + `/api/v1/*` + `/-/healthy`) — no nginx fronting because there is no UI in this stack (P1: Grafana lives elsewhere).

| File | Role |
|---|---|
| `prometheus/service/Prometheus__SG__Helper.py` | `ensure_security_group(region, stack_name, caller_ip)` — idempotent; ingress on port 9090; ASCII-only Description; duplicate-ingress swallowed. `delete_security_group(region, sg_id) -> bool`. |
| `prometheus/service/Prometheus__AMI__Helper.py` | `latest_al2023_ami_id(region)` (raises if none); `latest_healthy_ami_id(region)` filtered by `sg:purpose=prometheus` + `sg:ami-status=healthy` (empty if none). |
| `prometheus/service/Prometheus__Instance__Helper.py` | `list_stacks(region)` filtered by `sg:purpose=prometheus` + live states; `find_by_stack_name(region, name) -> Optional[dict]`; `terminate_instance(region, iid) -> bool`. |
| `prometheus/service/Prometheus__Tags__Builder.py` | Pure mapper. Builds 6-tag list (Name + sg:purpose + sg:section + sg:stack-name + sg:allowed-ip + sg:creator). Name uses `PROM_NAMING.aws_name_for_stack` (prefix never doubled). Empty creator → `'unknown'`. |
| `prometheus/service/Prometheus__AWS__Client.py` (modified) | Skeleton becomes composition shell — `sg`/`ami`/`instance`/`tags` slots wired by `setup()`. Launch helper wired in 6f.4a. |

## Departures from the `sp os` template

- **Port 9090, not 443.** Prometheus serves its UI on its own port; no nginx terminator. `PROMETHEUS_PORT_EXTERNAL = 9090` exported as a module constant + locked by test.
- **No `Safe_Str__Prom__Password` thread.** Prometheus has no built-in auth (P1) — caller_ip /32 SG-ingress is the only auth boundary. Same shape as `sp os` SG helper but no password-related behaviour to test.
- Otherwise byte-for-byte parity with the `sp os` 5c shape — same `_Fake_Boto_EC2` test pattern, same idempotency semantics, same `sg:purpose` filter.

## Tests

23 new tests, all green:

| Group | Tests |
|---|---|
| `Prometheus__AWS__Client` (extends 6a) | +2 — `setup()` wires all 4 helpers; `setup()` returns self for chaining. (Was 1; now 3.) |
| `Prometheus__SG__Helper` | 7 — port constant is 9090, create-when-missing, reuse existing, duplicate-ingress swallowed, other ingress errors propagate, delete success, delete failure → False |
| `Prometheus__AMI__Helper` | 4 — latest_al2023 returns most recent + filter shape, raises when none, latest_healthy filter shape (`sg:purpose=prometheus`), empty when none |
| `Prometheus__Instance__Helper` | 6 — list_stacks filters + key shape, skips no-id, find_by_stack_name hit + miss, terminate success + failure → False |
| `Prometheus__Tags__Builder` | 4 — Name carries `prometheus-` prefix, never doubles, full 6-tag set present, empty creator → `'unknown'` |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 42 | 65 | +23 |

All 65 green. The earlier `Prometheus__AWS__Client` skeleton test (`test__instantiates_cleanly`) was extended in-place to also cover the new `setup()` wiring — kept at 3 tests in that file rather than spinning up a new one.

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__SG__Helper.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__AMI__Helper.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Instance__Helper.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Tags__Builder.py
M  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__AWS__Client.py
M  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__AWS__Client.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__SG__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__AMI__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Instance__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Tags__Builder.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Failure classification

**No surprises.** Sister-section template carries cleanly; the only deviation (port 9090 vs 443) was foreseen in the plan.

## Next

Step 6d — `Prometheus__HTTP__Base` + `Prometheus__HTTP__Probe`. Probe endpoints per plan 5: `GET /-/healthy` (200 → ready), `GET /api/v1/targets` (count + up state), `GET /api/v1/query?query=...` for the future `sp prom query` command.
