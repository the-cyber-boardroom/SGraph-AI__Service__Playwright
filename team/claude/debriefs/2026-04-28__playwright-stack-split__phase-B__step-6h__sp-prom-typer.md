# Phase B · Step 6h — `sp prom` / `sp prometheus` typer commands (Tier-2A)

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B step 5i (`6abf20b`) — `sp os` typer commands.
**Predecessor:** Phase B step 6g — `sp prom` FastAPI routes (`e4723ea`).

**Final slice — `sp prom` is now functionally complete end-to-end.**

---

## What shipped

| File | Role |
|---|---|
| `prometheus/cli/Renderers.py` | Tier-2A Rich renderers — `render_list` / `render_info` / `render_create` / `render_health`. Pure functions; mirrors the OS Renderers shape but adapted to the Prom schemas (no password rendered anywhere — locked by test; `prometheus_url` instead of `dashboards_url` + `os_endpoint`; `targets_total` / `targets_up` instead of `node_count` / `active_shards`). |
| `scripts/prometheus.py` | Typer app — 5 commands (`create` / `list` / `info` / `delete` / `health`). Each command body ~5 lines: build request, call `Prometheus__Service().setup()`, render via Renderers. |
| `scripts/provision_ec2.py` (modified) | Mounts `sp prometheus` (long) + `sp prom` (short alias, hidden) via `add_typer` after the existing `sp opensearch` / `sp os` mounts. |

## Departures from the `sp os` 5i template

- **No `--password` flag on `create`.** Prometheus has no built-in auth (P1).
- **Health flags renamed**: `--user` / `--password` are still there for nginx-wrapped variants but default to empty (vs OS where `--user='admin'` is the default).
- **Renderers drop password line** entirely from `render_create`. Test asserts `'password' not in out.lower()`.

## Tests

9 new tests:

| Group | Tests |
|---|---|
| `scripts/prometheus.py` smoke | 3 — top-level `--help` lists 5 commands; `create --help` shows `--region` + `--instance-type`; `health --help` shows `--user` + `--password` |
| `Renderers` | 6 — list (empty + non-empty), info (all fields), create (URL + targets count + **no password leaked**), health (healthy + unhealthy with `-1` sentinels rendering as `'—'`) |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 161 | 170 | +9 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/cli/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/cli/Renderers.py
A  scripts/prometheus.py
M  scripts/provision_ec2.py                                                          (added 3 lines for sp prom + sp prometheus add_typer mounts)
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/cli/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/cli/test_Renderers.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/cli/test_typer_app.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## `sp prom` summary — what's now live

```
sp prom create [name] [--region] [--instance-type]
sp prom list                   [--region]
sp prom info <name>            [--region]
sp prom delete <name>          [--region]
sp prom health <name>          [--region] [--user] [--password]
```

Plus the matching FastAPI surface:

```
POST   /prometheus/stack
GET    /prometheus/stacks
GET    /prometheus/stack/{name}
DELETE /prometheus/stack/{name}
GET    /prometheus/stack/{name}/health
```

## Failure classification

**No surprises.** The `sp os` 5i template ports cleanly. P1 sign-off ("no admin password / no Dashboards") shrinks the surface predictably.

## Next

Phase B step 6 (`sp prom`) is **complete**. Up next:

1. **Phase B step 7** — `sp vnc` (browser-viewer sister section): chromium + nginx + mitmproxy. ~9 slices following the same template, plus the N5 interceptor-resolution layer.
2. **Phase C** — strip the Playwright EC2 down to 2 containers. Cannot ship until B7 has `sp vnc` compose fragments.
3. **Phase D** — command cleanup (`sp vault-*` regroup, `*-ami` regroup, drop `forward-*`).
