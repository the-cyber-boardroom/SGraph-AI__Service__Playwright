# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Cli__SG_Edge__Waker
# Typer app for `sg edge waker` — inspect / debug the Edge Waker.
#
#   status        GET /__edge__/status via local in-process waker app (py3.12)
#   invoke <route> invoke a waker route locally: health|status|reconcile|idle-check
#   logs          tail Edge Waker Lambda log group  [Slice 5 — deployed Lambda]
#
# The waker app (Fast_API__Edge_Waker) requires osbot-fast-api-serverless which
# needs Python ≥3.12.  Both commands skip cleanly on 3.11 (exit 2 + hint).
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console

app = typer.Typer(name='waker', help='Edge Waker debug and diagnostic verbs.', no_args_is_help=True)

_SLICE5 = '\n  [dim]⌛  Requires Slice 5 (deployed Lambda + CloudWatch Logs wiring)[/]\n'
_PY312  = 'osbot-fast-api-serverless requires Python ≥3.12 — re-run with python3.12'


@app.command(name='status', help='GET /__edge__/status via local in-process waker app (requires py3.12).')
def status():
    c = Console(highlight=False)
    try:
        import asyncio
        from httpx import AsyncClient
        from sg_compute_specs.sg_edge.lambdas.edge_waker.Fast_API__Edge_Waker import Fast_API__Edge_Waker
        waker = Fast_API__Edge_Waker()
        waker.setup()

        async def _get():
            async with AsyncClient(app=waker.app, base_url='http://test') as ac:
                return await ac.get('/__edge__/status')

        resp = asyncio.run(_get())
        c.print()
        c.print(f'  Status : {resp.status_code}')
        c.print(f'  Body   : {resp.text[:800]}')
        c.print()
    except ImportError:
        c.print(f'\n  [yellow]⚠[/]  {_PY312}\n')
        raise typer.Exit(2)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)


@app.command(name='invoke', help='Invoke a waker route locally (health|status|reconcile|idle-check, requires py3.12).')
def invoke(route: str = typer.Argument(..., help='Route: health | status | reconcile | idle-check')):
    c    = Console(highlight=False)
    path = f'/__edge__/{route}'
    try:
        import asyncio
        from httpx import AsyncClient
        from sg_compute_specs.sg_edge.lambdas.edge_waker.Fast_API__Edge_Waker import Fast_API__Edge_Waker
        waker = Fast_API__Edge_Waker()
        waker.setup()

        async def _get():
            async with AsyncClient(app=waker.app, base_url='http://test') as ac:
                return await ac.get(path)

        resp = asyncio.run(_get())
        c.print()
        c.print(f'  Route  : {path}')
        c.print(f'  Status : {resp.status_code}')
        c.print(f'  Body   : {resp.text[:800]}')
        c.print()
    except ImportError:
        c.print(f'\n  [yellow]⚠[/]  {_PY312}\n')
        raise typer.Exit(2)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)


@app.command(name='logs', help='Tail the Edge Waker Lambda log group (Slice 5).')
def logs():
    Console(highlight=False).print(_SLICE5)
