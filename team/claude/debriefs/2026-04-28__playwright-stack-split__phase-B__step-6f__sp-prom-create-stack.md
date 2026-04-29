# Phase B · Step 6f — `sp prom` user-data + compose + config generator + launch + wire `create_stack`

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B steps 5f.1 → 5f.4b (`363341c` → `2b21126`) — `sp os` user-data + compose + create_stack.
**Predecessor:** Phase B step 6e — `sp prom` Service read paths (`2b5b93b`).

**Compressed slice.** Per operator's note, the `sp os` 5f.1 → 5f.4b sequence (5 commits) lands here as one commit because the `sp prom` surface is simpler — no admin password to thread, no `vm.max_map_count` bump.

---

## What shipped

End-to-end `create_stack` working in pure logic. Service composes name_gen + ip_detector + ami helper + sg helper + tags builder + compose template + **config generator** (new — renders `prometheus.yml`) + user-data builder + launch helper.

| File | Role |
|---|---|
| `prometheus/service/Prometheus__Compose__Template.py` | docker-compose.yml renderer — 3 services (`prometheus` + `cadvisor` + `node-exporter`) on `sg-net` bridge. Bind-mounts `/opt/sg-prometheus/prometheus.yml` into the prometheus container. `--storage.tsdb.retention.time=24h` per P2. |
| `prometheus/service/Prometheus__Config__Generator.py` | `prometheus.yml` renderer. Always emits baseline cadvisor + node-exporter scrape jobs + one block per caller-supplied `Schema__Prom__Scrape__Target`. |
| `prometheus/service/Prometheus__User_Data__Builder.py` | EC2 UserData bash. Installs Docker via `dnf`, writes both `prometheus.yml` and compose YAML, runs `docker compose up -d`. **No `vm.max_map_count` bump** (Prom doesn't need it). |
| `prometheus/service/Prometheus__Launch__Helper.py` | `run_instance(...)` — base64 UserData, `MinCount=MaxCount=1`, `DEFAULT_INSTANCE_TYPE='t3.medium'`. |
| `prometheus/service/Prometheus__AWS__Client.py` (modified) | `setup()` now wires the 5th slot (`launch`). |
| `prometheus/service/Prometheus__Service.py` (modified) | New slots: `compose_template` / `config_generator` / `user_data_builder`. New method: `create_stack(request, creator='')` — composes all helpers; targets_count derived from `len(request.scrape_targets)`. |

## Departures from the `sp os` 5f sequence

- **No password thread.** OS had `secrets.token_urlsafe(24)` + `Safe_Str__OS__Password` defaulting + a defensive "password never appears in user-data" test. None of that exists for Prom (P1 — no built-in auth).
- **No `vm.max_map_count` bump.** OS bumps to `262144` (required for Lucene); Prom doesn't need it. User-data is shorter.
- **Two YAMLs in user-data, not one.** OS embeds compose; Prom embeds compose **and** prometheus.yml (each in its own heredoc).
- **Smaller default instance.** `t3.medium` (2 vCPU / 4 GB) vs OS's `t3.large`.
- **No Dashboards container** (P1 — locked by test).
- **One commit, not five** — the four 5f sub-slices compress cleanly because the surface is simpler.

## Tests

47 new tests, all green:

| Group | Tests |
|---|---|
| `Prometheus__Compose__Template` | 11 — defaults / 24h retention / custom retention / custom images / no leftover placeholders / canonical container names / sg-net network / **no Grafana or Dashboards** / bind-mount prometheus.yml / port 9090 exposed / placeholders match constant |
| `Prometheus__Config__Generator` | 6 — baseline-only when no targets / empty list / one baked target / multiple targets in order / baseline always before baked / single-quoted host:port |
| `Prometheus__User_Data__Builder` | 12 — shebang / strict bash / canonical log / stack+region substitution / compose heredoc / prometheus.yml heredoc / no leftover placeholders / dnf install / compose plugin / **no `vm.max_map_count`** / compose-up runs in compose dir / placeholders match / canonical paths |
| `Prometheus__Launch__Helper` | 11 — returns instance id / base64 UserData / SG attached / tags attached / **default `t3.medium`** / custom type / profile optional + attached / `MinCount=MaxCount=1` / empty response raises / boto failure propagates |
| `Prometheus__AWS__Client.setup()` | +1 (extended in-place from 4-helper to 5-helper assertion; null-check now includes `launch` too) |
| `Prometheus__Service.create_stack` | 6 — empty request resolves all defaults / overrides take priority / scrape_targets flow into config_generator + targets_count / sg ingress uses resolved caller_ip / launch call carries correct user-data + tags / user-data takes both compose + prometheus.yml |
| `Prometheus__Service.setup()` | extended to verify all 8 helpers (5 read-path + 3 new) |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 105 | 152 | +47 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Compose__Template.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Config__Generator.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__User_Data__Builder.py
A  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Launch__Helper.py
M  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__AWS__Client.py
M  sgraph_ai_service_playwright__cli/prometheus/service/Prometheus__Service.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Compose__Template.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Config__Generator.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__User_Data__Builder.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Launch__Helper.py
M  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__AWS__Client.py
M  tests/unit/sgraph_ai_service_playwright__cli/prometheus/service/test_Prometheus__Service.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Failure classification

**No surprises.** Sister-section template ports cleanly; the four 5f sub-slices compress as predicted because the surface is simpler.

## Next

Step 6g — `Routes__Prometheus__Stack` (5 FastAPI routes mirroring `Routes__OpenSearch__Stack`).
