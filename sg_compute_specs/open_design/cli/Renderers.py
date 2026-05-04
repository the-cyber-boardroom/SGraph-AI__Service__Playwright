# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open Design CLI Renderers
# Pure Rich renderers. No AWS calls, no business logic.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Response import Schema__Open_Design__Create__Response
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Info             import Schema__Open_Design__Info
from sg_compute_specs.open_design.schemas.Schema__Open_Design__List             import Schema__Open_Design__List


def _state_colour(state: str) -> str:
    return {'running': 'green', 'pending': 'yellow', 'stopping': 'yellow',
            'stopped': 'red', 'shutting-down': 'red', 'terminated': 'red'}.get(state, 'white')


def _secs(ms: int) -> str:
    return f'{ms / 1000:.1f}s'


def render_list(listing: Schema__Open_Design__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No open-design stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name' , style='bold')
    t.add_column('instance-id', style='dim')
    t.add_column('state')
    t.add_column('url'        , style='cyan')
    t.add_column('region'     , style='dim')
    t.add_column('ollama')
    for info in listing.stacks:
        t.add_row(
            info.stack_name                                              ,
            info.instance_id                                             ,
            f'[{_state_colour(info.state)}]{info.state}[/]'             ,
            info.viewer_url or '—'                                       ,
            info.region                                                  ,
            '[green]yes[/]' if info.has_ollama else '[dim]no[/]'        ,
        )
    c.print(t)


def render_info(info: Schema__Open_Design__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]Open Design[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16, no_wrap=True)
    t.add_column()
    t.add_row('url'         , info.viewer_url        or '—')
    t.add_row('region'      , info.region             or '—')
    t.add_row('instance'    , info.instance_type      or '—')
    t.add_row('ami'         , info.ami_id             or '—')
    t.add_row('public-ip'   , info.public_ip          or '—')
    t.add_row('caller-ip'   , info.caller_ip          or '—')
    t.add_row('sg-id'       , info.security_group_id  or '—')
    t.add_row('ollama'      , '[green]yes[/]' if info.has_ollama else '[dim]no[/]')
    t.add_row('uptime'      , f'{info.uptime_seconds}s' if info.uptime_seconds else '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Open_Design__Create__Response, c: Console) -> None:
    info = resp.stack_info
    c.print()
    c.print(Panel(f'[bold green]🚀  Launching open-design stack[/]  ·  {info.stack_name}',
                  border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id : [dim]{info.instance_id}[/]')
    c.print(f'  region      : {info.region}')
    c.print(f'  ami         : {info.ami_id}')
    c.print(f'  instance    : {info.instance_type}')
    c.print(f'  ollama      : {"yes" if info.has_ollama else "no"}')
    c.print(f'  submitted in: {_secs(resp.elapsed_ms)}')
    c.print()
    c.print(f'  [dim]Once running:  ec2 open-design info {info.stack_name} --region {info.region}[/]')
    c.print(f'  [dim]Wait healthy:  ec2 open-design health {info.stack_name} --region {info.region}[/]')
    c.print()


def render_delete(stack_name: str, deleted: bool, c: Console) -> None:
    if deleted:
        c.print(f'  [green]deleted[/] {stack_name}')
    else:
        c.print(f'  [red]failed to delete[/] {stack_name}')
