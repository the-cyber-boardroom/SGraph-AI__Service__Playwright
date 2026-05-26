# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode CLI Renderers
# Pure Rich renderers. No AWS calls, no business logic.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Renderers__Base                   import humanize_uptime
from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Response import Schema__Vscode__Create__Response
from sg_compute_specs.vscode.schemas.Schema__Vscode__Info             import Schema__Vscode__Info


def _state_colour(state: str) -> str:
    return {'running': 'green', 'pending': 'yellow', 'stopping': 'yellow',
            'stopped': 'red', 'shutting-down': 'red', 'terminated': 'red'}.get(state, 'white')


def _secs(ms: int) -> str:
    return f'{ms / 1000:.1f}s'


def render_info(info: Schema__Vscode__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]VS Code[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16, no_wrap=True)
    t.add_column()
    t.add_row('distribution', info.distribution      or '—')
    t.add_row('ingress'     , info.ingress           or '—')
    t.add_row('region'      , info.region            or '—')
    t.add_row('instance'    , info.instance_type     or '—')
    t.add_row('ami'         , info.ami_id            or '—')
    t.add_row('public-ip'   , info.public_ip         or '—')
    t.add_row('sg-id'       , info.security_group_id or '—')
    t.add_row('disk-gb'     , str(info.disk_size_gb) if info.disk_size_gb else '—')
    t.add_row('pricing'     , '[cyan]spot[/]' if info.spot else 'on-demand')
    t.add_row('uptime'      , humanize_uptime(info.uptime_seconds))
    c.print(t)
    c.print()
    if info.vscode_url:
        c.print(f'  [bold]editor:[/]  [cyan]{info.vscode_url}[/]')
    if info.ssm_forward:
        c.print(f'  [dim]Tunnel:   sg vscode forward {info.stack_name} --region {info.region}[/]')
        c.print(f'  [dim]  (raw)   {info.ssm_forward}[/]')
    if info.ssm_session:
        c.print(f'  [dim]Terminal: sg vscode connect {info.stack_name} --region {info.region}[/]')
    c.print()


def render_create(resp: Schema__Vscode__Create__Response, c: Console) -> None:
    info = resp.stack_info
    c.print()
    c.print(Panel(f'[bold green]Launching vscode stack[/]  ·  {info.stack_name}',
                  border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id  : [dim]{info.instance_id}[/]')
    c.print(f'  region       : {info.region}')
    c.print(f'  ami          : {info.ami_id}')
    c.print(f'  instance     : {info.instance_type}')
    c.print(f'  distribution : {info.distribution}')
    c.print(f'  ingress      : {info.ingress}')
    c.print(f'  submitted in : {_secs(resp.elapsed_ms)}')
    c.print()
    if resp.password:
        c.print(f'  [bold yellow]editor password[/] (shown once): [bold]{resp.password}[/]')
        c.print()
    c.print(f'  [dim]Wait:    sg vscode wait {info.stack_name} --region {info.region}[/]')
    c.print(f'  [dim]Tunnel:  sg vscode forward {info.stack_name} --region {info.region}[/]')
    c.print(f'  [dim]  then open [cyan]{info.vscode_url}[/] in your browser[/]')
    c.print()
