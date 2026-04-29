# Phase B · Step 7h — `sp vnc` typer commands (Tier-2A)

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6h (`c81a1b1`) — `sp prom` typer.
**Predecessor:** Phase B step 7g — `sp vnc` FastAPI routes (`2eb7bb7`).

**Final slice — `sp vnc` is now functionally complete end-to-end.**

---

## What shipped

| File | Role |
|---|---|
| `vnc/cli/Renderers.py` | Tier-2A Rich renderers — `render_list` / `render_info` / `render_create` / `render_health` / `render_flows` / `render_interceptors`. Pure functions; mirrors the prom shape with two extras (flows + interceptors). |
| `scripts/vnc.py` | Typer app — **7 commands** (`create` / `list` / `info` / `delete` / `health` / `flows` / `interceptors`). |
| `scripts/provision_ec2.py` (modified) | Mounts `sp vnc` (single name; no short alias per N1) via `add_typer` after the existing `sp prometheus` mount. |

## Departures from the `sp prom` 6h template

- **7 commands, not 5.** `sp vnc flows <name>` peeks the mitmweb flow listing (per N4 no auto-export). `sp vnc interceptors` lists the baked example names — no service call needed; reads `list_examples()` directly from the resolver.
- **N5 interceptor flags on `create`.**
  - `--interceptor <name>` — load baked example by name
  - `--interceptor-script <path>` — read a local `.py` file and embed its source verbatim
  - Both flags omitted → `Schema__Vnc__Interceptor__Choice` defaults to NONE → no-op interceptor (default-off)
  - Both flags provided → `typer.BadParameter` (mutually exclusive)
- **No short alias.** Per N1, `sp vnc` is the only name (working title `sp nvm` was dropped).

## Tests

15 new tests:

| Group | Tests |
|---|---|
| `scripts/vnc.py` smoke (CliRunner) | 4 — top-level `--help` lists 7 commands; `create --help` shows both `--interceptor` and `--interceptor-script`; `health --help` shows `--user`/`--password`; `interceptors` command runs and lists 3 baked examples |
| `Renderers` | 11 — list (empty + non-empty), info (all fields incl. interceptor name; NONE renders as `'none'`), create (password warning + self-signed TLS warning + interceptor label), health (healthy + unhealthy with `-1` sentinel rendering as `'—'`), flows (empty + with summaries incl. status_code=0 → `'—'`), interceptors (empty + non-empty) |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 174 | 189 | +15 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/cli/__init__.py
A  sgraph_ai_service_playwright__cli/vnc/cli/Renderers.py
A  scripts/vnc.py
M  scripts/provision_ec2.py                                                          (added 3 lines for sp vnc add_typer mount)
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/cli/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/cli/test_Renderers.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/cli/test_typer_app.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## `sp vnc` summary — what's now live

```
sp vnc create [name] [--region] [--instance-type]
                     [--interceptor <name> | --interceptor-script <path>]
sp vnc list                   [--region]
sp vnc info <name>            [--region]
sp vnc delete <name>          [--region]
sp vnc health <name>          [--region] [--user] [--password]
sp vnc flows <name>           [--region] [--user] [--password]
sp vnc interceptors                                              # No AWS call — lists baked example names
```

Plus the matching FastAPI surface:

```
POST   /vnc/stack
GET    /vnc/stacks
GET    /vnc/stack/{name}
DELETE /vnc/stack/{name}
GET    /vnc/stack/{name}/health
GET    /vnc/stack/{name}/flows
```

## Failure classification

**No surprises.** The N5 typer surface is the only deviation from the prom 6h template (mutually-exclusive `--interceptor` / `--interceptor-script` flags), and it landed cleanly because the resolver's three-shape contract was already locked.

## Phase B step 7 (`sp vnc`) is **complete**

What's next:

1. **Phase C** — strip the Playwright EC2 down to 2 containers. Now unblocked by both `sp prom` and `sp vnc` being live.
   - C.1 — Move `COMPOSE_SVC_BROWSER` + `COMPOSE_SVC_BROWSER_PROXY` to sp vnc; the prom-related compose services to sp prom; fluent-bit to sp os.
   - C.2 — Delete the moved containers from `provision_ec2.py:967-979`. Container-count assertion drops from 9 to 2.
   - C.3 — Drop ports 9090 / 3000 / 5001 / 8080 from the SG.
   - C.4 — Drop `IAM__PROMETHEUS_RW_POLICY_ARN` from `IAM__OBSERVABILITY_POLICY_ARNS`.
   - C.5 — Bake new AMI; tag previous as `superseded`.
   - C.6 — Update reality doc.

2. **Phase D** — command cleanup (`sp vault-*` regroup, `*-ami` regroup, drop `forward-*`, move `sp metrics` → `sp prom metrics`).
