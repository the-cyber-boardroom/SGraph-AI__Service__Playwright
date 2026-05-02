# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama CLI Renderers
# Pure Rich renderers. No AWS calls, no business logic.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Response import Schema__Ollama__Create__Response
from sg_compute_specs.ollama.schemas.Schema__Ollama__Info             import Schema__Ollama__Info
from sg_compute_specs.ollama.schemas.Schema__Ollama__List             import Schema__Ollama__List


def _state_colour(state: str) -> str:
    return {'running': 'green', 'pending': 'yellow', 'stopping': 'yellow',
            'stopped': 'red', 'shutting-down': 'red', 'terminated': 'red'}.get(state, 'white')


def _secs(ms: int) -> str:
    return f'{ms / 1000:.1f}s'


def render_list(listing: Schema__Ollama__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No ollama stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'  , style='bold')
    t.add_column('instance-id' , style='dim')
    t.add_column('state')
    t.add_column('model')
    t.add_column('api-url'     , style='cyan')
    t.add_column('region'      , style='dim')
    t.add_column('gpu')
    for info in listing.stacks:
        t.add_row(
            info.stack_name                                                 ,
            info.instance_id                                                ,
            f'[{_state_colour(info.state)}]{info.state}[/]'                ,
            info.model_name or '—'                                          ,
            info.api_base_url or '—'                                        ,
            info.region                                                     ,
            f'[green]{info.gpu_count}[/]' if info.gpu_count else '[dim]0[/]',
        )
    c.print(t)


def render_info(info: Schema__Ollama__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]Ollama[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16, no_wrap=True)
    t.add_column()
    t.add_row('model'      , info.model_name         or '—')
    t.add_row('api-url'    , info.api_base_url        or '—')
    t.add_row('region'     , info.region              or '—')
    t.add_row('instance'   , info.instance_type       or '—')
    t.add_row('ami'        , info.ami_id              or '—')
    t.add_row('private-ip' , info.private_ip          or '—')
    t.add_row('public-ip'  , info.public_ip           or '—')
    t.add_row('sg-id'      , info.security_group_id   or '—')
    t.add_row('gpu-count'  , str(info.gpu_count))
    t.add_row('uptime'     , f'{info.uptime_seconds}s' if info.uptime_seconds else '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Ollama__Create__Response, c: Console) -> None:
    info = resp.stack_info
    c.print()
    c.print(Panel(f'[bold green]Launching ollama stack[/]  ·  {info.stack_name}',
                  border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id : [dim]{info.instance_id}[/]')
    c.print(f'  region      : {info.region}')
    c.print(f'  ami         : {info.ami_id}')
    c.print(f'  instance    : {info.instance_type}')
    c.print(f'  model       : {info.model_name}')
    c.print(f'  submitted in: {_secs(resp.elapsed_ms)}')
    c.print()
    c.print(f'  [dim]Once running:  ec2 ollama info {info.stack_name} --region {info.region}[/]')
    c.print(f'  [dim]Wait healthy:  ec2 ollama health {info.stack_name} --region {info.region}[/]')
    c.print()


def render_delete(stack_name: str, deleted: bool, c: Console) -> None:
    if deleted:
        c.print(f'  [green]deleted[/] {stack_name}')
    else:
        c.print(f'  [red]failed to delete[/] {stack_name}')
