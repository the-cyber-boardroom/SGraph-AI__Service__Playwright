# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Cli__SG_Edge
# Typer umbrella for `sg edge` / `sg ed` commands (the whole SG/Edge tier).
#
#   status      fleet snapshot: proxy count, active slugs, zero_streak, target
#   idle-check  idle-teardown counter step (increment/reset now; drain = Slice 5)
#   boot        cold-cold: boot one proxy if fleet is empty               [Slice 5]
#   reconcile   convergent scale check — scale UP toward target            [Slice 5]
#   drain       force teardown of the whole fleet                          [Slice 5]
#
#   dns         DNS-as-registry diagnostics  (Cli__SG_Edge__Dns)
#   proxy       proxy-asset helpers          (Cli__SG_Edge__Proxy)
#   bench       doc-05 measurement harness   (Cli__SG_Edge__Bench)
#   waker       Edge Waker debug verbs       (Cli__SG_Edge__Waker)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from rich.console import Console

app = typer.Typer(name='edge', help='SG/Edge — central edge tier (proxy fleet + Edge Waker).', no_args_is_help=True)

_SLICE5 = '\n  [dim]⌛  Requires Slice 5 (EC2 launcher/terminator not yet wired)[/]\n'

from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Dns       import app as _dns_app
from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Proxy     import app as _proxy_app
from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Bench     import app as _bench_app
from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Waker     import app as _waker_app
from sg_compute_specs.sg_edge.local.cli.Cli__SG_Edge__Local import app as _local_app
from sg_compute_specs.sg_edge.tui.cli.Cli__SG_Edge__Tui    import app as _tui_app

app.add_typer(_local_app, name='local', help='Local deployment (setup / usage / teardown — no AWS).')
app.add_typer(_dns_app,   name='dns',   help='DNS-as-registry diagnostics (read-only).')
app.add_typer(_proxy_app, name='proxy', help='Proxy-asset helpers (pure, no AWS).')
app.add_typer(_bench_app, name='bench', help='SG/Edge bench harness (doc-05).')
app.add_typer(_waker_app, name='waker', help='Edge Waker debug and diagnostic verbs.')
app.add_typer(_tui_app,   name='tui',   help='Exploratory TUI screens (Textual; lazy import).')

_reconciler_factory = None                                                       # tests assign a callable(parent) → SG_Edge__Fleet__Reconciler


def _parent_from(parent: str) -> str:                                            # hard-coded edge.sg-labs.app is the final fallback (create/destroy-at-will zone)
    from sg_compute_specs.sg_edge.local.sg_edge_local__config import SG_EDGE__AWS_PARENT
    return (parent
            or os.environ.get('SG_EDGE__PARENT_DOMAIN', '')
            or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', '')
            or SG_EDGE__AWS_PARENT)


def _reconciler(parent: str):
    if _reconciler_factory is not None:
        return _reconciler_factory(parent)
    from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                    import SG_Edge__DNS__Helper
    from sg_compute_specs.sg_edge.service.SG_Edge__Fleet__Reconciler              import SG_Edge__Fleet__Reconciler
    from sg_compute_specs.sg_edge.lambdas.edge_waker.edge_waker__config            import edge_proxy_target_count, edge_idle_teardown_threshold
    return SG_Edge__Fleet__Reconciler(
        dns            = SG_Edge__DNS__Helper(),
        parent         = parent,
        target_count   = edge_proxy_target_count(),
        idle_threshold = edge_idle_teardown_threshold(),
    )


@app.command(name='status', help='Fleet snapshot — proxy count, active slugs, zero_streak, desired target.')
def status(
    parent     : str  = typer.Option('', '--parent', '-p', envvar='SG_EDGE__PARENT_DOMAIN', help='Edge parent domain'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    c   = Console(highlight=False)
    par = _parent_from(parent)
    try:
        rec        = _reconciler(par)
        dns        = rec.dns
        ips        = dns.list_proxy_ips(par)
        slugs      = dns.list_active_slugs(par)
        state_rec  = dns.read_state(par)
        target     = rec.desired_target()
        if output_json:
            c.print(json.dumps({
                'parent'      : par,
                'proxy_count' : len(ips),
                'proxy_ips'   : ips,
                'active_slugs': slugs,
                'zero_streak' : int(state_rec.zero_streak),
                'desired'     : target,
            }, indent=2))
            return
        c.print()
        c.print(f'  [bold]SG/Edge status[/]  parent=[cyan]{par}[/]')
        c.print()
        c.print(f'  Proxy count   : {len(ips)}  [dim](desired: {target})[/]')
        if ips:
            c.print(f'  Proxy IPs     : {", ".join(ips)}')
        c.print(f'  Active slugs  : {len(slugs)}  [dim]({", ".join(slugs) or "none"})[/]')
        c.print(f'  Zero streak   : {int(state_rec.zero_streak)}')
        c.print()
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)


@app.command(name='idle-check', help='Idle-teardown counter step — increment / reset / drain.')
def idle_check(
    parent     : str  = typer.Option('', '--parent', '-p', envvar='SG_EDGE__PARENT_DOMAIN', help='Edge parent domain'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    c   = Console(highlight=False)
    par = _parent_from(parent)
    try:
        result = _reconciler(par).idle_check()
    except NotImplementedError:
        c.print('\n  [yellow]⚠[/]  Teardown threshold reached but _terminator not wired (Slice 5).\n'
                '  [dim]   DNS _state record shows the streak; fleet not drained.[/]\n')
        raise typer.Exit(2)
    except Exception as exc:
        c.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        c.print(json.dumps(result.json(), indent=2))
        return
    action = str(result.action)
    icon   = {'reset': '[green]✓[/]', 'increment': '[yellow]→[/]', 'teardown': '[red]✗[/]'}.get(action, '·')
    c.print()
    c.print(f'  {icon}  [bold]idle-check[/]  action=[cyan]{action}[/]  '
            f'active={result.active}  zero_streak={result.zero_streak}')
    if list(result.drained):
        c.print(f'  Drained: {", ".join(list(result.drained))}')
    c.print()


@app.command(name='boot', help='Cold-cold: ensure one proxy is booting if the fleet is empty (Slice 5).')
def boot():
    Console(highlight=False).print(_SLICE5)


@app.command(name='reconcile', help='Convergent scale check — scale UP toward target proxy count (Slice 5).')
def reconcile():
    Console(highlight=False).print(_SLICE5)


@app.command(name='drain', help='Force teardown of the whole fleet (Slice 5).')
def drain():
    Console(highlight=False).print(_SLICE5)
