# `sp vnc` — Tier-2A (CLI)

The typer surface — what the operator sees when they run `sp vnc`.

## Entry point

`scripts/vnc.py` defines `app = typer.Typer(...)`. Mounted on the main `sp` app via `add_typer` in `scripts/provision_ec2.py`:

```python
from scripts.vnc import app as _vnc_app
app.add_typer(_vnc_app, name='vnc')
```

No short alias — per N1, the section is `sp vnc` only (working title `sp nvm` was dropped).

## Commands

```
sp vnc create [name] [--region] [--instance-type]
                     [--interceptor <name> | --interceptor-script <path>]
sp vnc list                   [--region]
sp vnc info <name>            [--region]
sp vnc delete <name>          [--region]
sp vnc health <name>          [--region] [--user] [--password]
sp vnc flows <name>           [--region] [--user] [--password]
sp vnc interceptors                                              # No AWS call
```

## N5 interceptor flags on `create`

The `--interceptor` and `--interceptor-script` flags are **mutually exclusive**:

| Flag | Effect |
|---|---|
| `--interceptor <name>` | Loads a baked example by name. Validates against `Vnc__Interceptor__Resolver.list_examples()`. |
| `--interceptor-script <path>` | Reads a local Python file; embeds its source as `inline_source` in the request schema (max 32 KB). |
| neither | Defaults to `Schema__Vnc__Interceptor__Choice()` → `kind=NONE` → mitmproxy starts with a no-op interceptor. |
| both | `typer.BadParameter` raised in the typer layer (before service is called). |

Locked by smoke tests at `tests/unit/sgraph_ai_service_playwright__cli/vnc/cli/test_typer_app.py`.

## Renderers (Tier-2A)

`cli/vnc/cli/Renderers.py` — pure functions; each accepts a Type_Safe schema + a `rich.Console`:

| Renderer | Used by |
|---|---|
| `render_list(listing, c)` | `sp vnc list` |
| `render_info(info, c)` | `sp vnc info` |
| `render_create(resp, c)` | `sp vnc create` (includes "stash this password now" banner) |
| `render_health(health, c)` | `sp vnc health` |
| `render_flows(flows, c)` | `sp vnc flows` |
| `render_interceptors(names, c)` | `sp vnc interceptors` |

State→colour mapping mirrors the `sp os` / `sp prom` Renderers. Tests capture output via `Console(file=StringIO(...))`.

## Service seam

`scripts/vnc.py::_service()` returns a freshly-`setup()`-wired `Vnc__Service`. Tests don't override this — they use the underlying `Vnc__Service.create_stack(...)` etc. directly.

## Where to read first

1. `scripts/vnc.py` — 110 lines, all 7 commands
2. `tests/unit/sgraph_ai_service_playwright__cli/vnc/cli/test_typer_app.py` — smoke via `CliRunner`
3. `tests/unit/sgraph_ai_service_playwright__cli/vnc/cli/test_Renderers.py` — Console capture pattern

Mounted on `sp` already. `sp vnc --help` lists 7 commands. Try it locally.
