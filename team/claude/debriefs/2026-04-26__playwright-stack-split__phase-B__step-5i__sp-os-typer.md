# Phase B · Step 5i — `sp os` / `sp opensearch` typer commands + Renderers

**Date:** 2026-04-26.
**Commit:** `6abf20b`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5h (FastAPI routes).

---

## What shipped

End-to-end CLI for the OpenSearch sister section. Two small focused files (one concern each, per operator's small-file discipline).

### `cli/opensearch/cli/Renderers.py` (~85 lines)

Pure Tier-2A Rich renderers — schema → human Rich output.

- `render_list(listing, console)` — table of stacks
- `render_info(info, console)` — single-stack detail panel
- `render_create(resp, console)` — create response with **loud password warning** + self-signed-TLS reminder
- `render_health(h, console)` — cluster + dashboards probe results; `-1` sentinels render as `—`

`_state_colour(state)` helper colour-codes `Enum__OS__Stack__State` (READY/RUNNING green, PENDING yellow, TERMINATED/TERMINATING red).

No service / AWS / network calls.

### `scripts/opensearch.py` (~75 lines)

Typer app with 5 commands — each body 3-5 lines:

```
create [name]   --region --instance-type --password
list             --region
info <name>      --region
delete <name>    --region
health <name>    --region --user --password
```

`_service()` seam returns `OpenSearch__Service().setup()`; tests can monkey-patch.

### Wiring into the main `sp` app

`scripts/provision_ec2.py` adds:

```python
from scripts.opensearch import app as _opensearch_app
app.add_typer(_opensearch_app, name='opensearch')
app.add_typer(_opensearch_app, name='os', hidden=True)
```

Mirrors the `sp el` / `sp elastic` pattern. Verified via `app.registered_groups` listing both `'opensearch'` and `'os'`.

## Tests

9 new tests across 2 focused files:

| File | Tests | Covers |
|---|---|---|
| `test_Renderers.py` | 8 | list empty / non-empty, info covers all fields, create includes password warning + TLS reminder, health healthy / unhealthy with `—` sentinels |
| `test_typer_app.py` | 3 | `--help` exposes 5 commands; `create --help` and `health --help` show expected options |

Renderer tests capture Rich output via `Console(file=StringIO)`. Typer tests use `typer.testing.CliRunner`.

## Phase B `sp os` — functionally complete

```
sp os --help          ← typer (5i)
   ↓
OpenSearch__Service   ← orchestrator (5e + 5f.4b)
   ↓
sg / ami / instance / launch / tags helpers (5c, 5f.4a)
http base / probe / mapper / ip-detector / name-gen / compose / user-data (5d, 5e, 5f)
   ↓
schemas + collections (5b)
primitives + enums (5a)
```

Plus FastAPI routes on `/opensearch/*` (5h).

Only deferred: 5g (dashboard generator + shared `Base__Dashboard__Generator` extracted from elastic — meaningful refactor across two sections, best done fresh).

## Files changed

```
A  scripts/opensearch.py
M  scripts/provision_ec2.py
A  sgraph_ai_service_playwright__cli/opensearch/cli/__init__.py
A  sgraph_ai_service_playwright__cli/opensearch/cli/Renderers.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/cli/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/cli/test_Renderers.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/cli/test_typer_app.py
```
