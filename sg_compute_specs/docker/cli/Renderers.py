# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: CLI Renderers
# Pure Rich renderers. No AWS calls, no business logic.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute_specs.docker.schemas.Schema__Docker__Create__Response import Schema__Docker__Create__Response
from sg_compute_specs.docker.schemas.Schema__Docker__Info             import Schema__Docker__Info
from sg_compute_specs.docker.schemas.Schema__Docker__List             import Schema__Docker__List


def _state_colour(state: str) -> str:
    return {'running': 'green', 'pending': 'yellow', 'stopping': 'yellow',
            'stopped': 'red', 'shutting-down': 'red', 'terminated': 'red'}.get(state.lower(), 'white')


def _secs(ms: int) -> str:
    return f'{ms / 1000:.1f}s'


def render_list(listing: Schema__Docker__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No docker stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'  , style='bold')
    t.add_column('instance-id' , style='dim')
    t.add_column('state')
    t.add_column('instance-type')
    t.add_column('public-ip'   , style='cyan')
    t.add_column('region'      , style='dim')
    t.add_column('uptime')
    for info in listing.stacks:
        state = str(info.state.value) if hasattr(info.state, 'value') else str(info.state)
        t.add_row(
            str(info.stack_name)                                ,
            str(info.instance_id)                              ,
            f'[{_state_colour(state)}]{state}[/]'             ,
            str(info.instance_type)                            ,
            str(info.public_ip) or '—'                         ,
            str(info.region)                                   ,
            f'{info.uptime_seconds}s' if info.uptime_seconds else '—',
        )
    c.print(t)


def render_info(info: Schema__Docker__Info, c: Console) -> None:
    state  = str(info.state.value) if hasattr(info.state, 'value') else str(info.state)
    colour = _state_colour(state)
    c.print()
    c.print(Panel(f'[bold]Docker[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{state}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16, no_wrap=True)
    t.add_column()
    t.add_row('region'       , str(info.region)            or '—')
    t.add_row('instance'     , str(info.instance_type)     or '—')
    t.add_row('ami'          , str(info.ami_id)            or '—')
    t.add_row('public-ip'    , str(info.public_ip)         or '—')
    t.add_row('sg-id'        , str(info.security_group_id) or '—')
    t.add_row('allowed-ip'   , str(info.allowed_ip)        or '—')
    t.add_row('docker'       , str(info.docker_version)    or '—')
    t.add_row('uptime'       , f'{info.uptime_seconds}s' if info.uptime_seconds else '—')
    t.add_row('launch-time'  , str(info.launch_time)       or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Docker__Create__Response, c: Console) -> None:
    info = resp.stack_info
    c.print()
    c.print(Panel(f'[bold green]Launching docker stack[/]  ·  {info.stack_name}',
                  border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id : [dim]{info.instance_id}[/]')
    c.print(f'  region      : {info.region}')
    c.print(f'  ami         : {info.ami_id}')
    c.print(f'  instance    : {info.instance_type}')
    c.print(f'  submitted in: {_secs(resp.elapsed_ms)}')
    c.print()
    c.print(f'  [dim]Once running:  sg-compute spec docker info {info.stack_name}[/]')
    c.print()


def render_delete(stack_name: str, deleted: bool, c: Console) -> None:
    if deleted:
        c.print(f'  [green]deleted[/] {stack_name}')
    else:
        c.print(f'  [red]failed to delete[/] {stack_name}')
