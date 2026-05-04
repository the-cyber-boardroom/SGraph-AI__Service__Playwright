# Phase B · Step 6e — `sp prom` Service orchestrator (read paths)

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B step 5e (`82afd0e`) — `sp os` Service orchestrator (read paths).
**Predecessor:** Phase B step 6d — `sp prom` HTTP base + probe (`23f82f8`).

---

## What shipped

4 small focused files (~25–90 lines each):

| File | Role |
|---|---|
| `prometheus/service/Caller__IP__Detector.py` | Section-local. Fetches `https://checkip.amazonaws.com`; tests subclass and override `fetch()`. |
| `prometheus/service/Random__Stack__Name__Generator.py` | `'<adjective>-<scientist>'` generator. Same vocabulary as elastic + opensearch (parity test). |
| `prometheus/service/Prometheus__Stack__Mapper.py` | Pure mapper. raw boto3 `describe_instances` detail dict → `Schema__Prom__Stack__Info`. Builds `prometheus_url = http://<ip>:9090/` (plain HTTP per P1; empty when AWS hasn't assigned the IP yet). State enum mapping locked by test. |
| `prometheus/service/Prometheus__Service.py` | Tier-1 orchestrator. Exposes `list_stacks` / `get_stack_info` / `delete_stack` / `health`. `create_stack` lands in step 6f.4b. `setup()` wires aws_client + probe + mapper + ip_detector + name_gen. |

`Prometheus__Service.health` composes the two probes from 6d:
- `probe.prometheus_ready(prometheus_url)` → bool (200 on `/-/healthy`)
- `probe.targets_status(prometheus_url)` → dict (parsed `/api/v1/targets`)
- A tiny `_count_targets()` helper at module level returns `(total, up)` from `data.activeTargets`. When the probe returns `{}` (network / non-200 / non-JSON), counts fall through to `(-1, -1)` sentinels — same convention as Schema__Prom__Health.

State flips to `READY` iff `prometheus_ready` returns True; otherwise stays at the EC2-state-derived value (RUNNING / PENDING / etc).

## Departures from the `sp os` template

- **No `compose_template` / `user_data_builder` slots yet** — those land in 6f. The `setup()` chain has 5 helpers, not 7.
- **No `create_stack`** — moved to 6f.4b alongside compose + user-data + launch.
- **Health is simpler** — no Dashboards probe (P1: no UI), no admin password thread, no doc-count concept.
- **`prometheus_url` mapper field uses port 9090** explicitly (vs OS using port 443 + 9200 separately).

## Tests

24 new tests, all green:

| Group | Tests |
|---|---|
| `Caller__IP__Detector` | 3 — defaults, strips trailing newline, rejects malformed |
| `Random__Stack__Name__Generator` | 3 — shape, lowercase + no-whitespace, **vocabulary parity with elastic** locked by test |
| `Prometheus__Stack__Mapper` | 5 — happy path (incl. `http://<ip>:9090/`), no public IP → empty URL, missing SG → empty SG, full state mapping, unknown state → UNKNOWN |
| `Prometheus__Service` — read paths | 12 — list (empty + 2 stacks), get (hit + miss), delete (hit + miss + terminate-failure), health (no instance / no public IP / ready+counts / not ready / ready-but-unreachable-targets), setup() returns self + wires 5 helpers |
| `_count_targets` exercised via `health` ready+targets test | (covered above) |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 81 | 105 | +24 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/service/Caller__IP__Detector.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Random__Stack__Name__Generator.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Stack__Mapper.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Service.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Caller__IP__Detector.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Random__Stack__Name__Generator.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Stack__Mapper.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Service.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 6f (combined per operator's note) — user-data skeleton + compose template + install steps + launch helper + wire `create_stack`. One commit.
