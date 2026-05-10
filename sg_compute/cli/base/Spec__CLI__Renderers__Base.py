# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Renderers__Base
# Default Rich renderers for the standard per-spec schemas.
# Specs can override by passing custom render callables via Schema__Spec__CLI__Spec.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table


def humanize_uptime(seconds) -> str:
    s = int(seconds or 0)
    if s <= 0:       return '—'
    if s < 60:       return f'{s}s'
    if s < 3600:     return f'{s // 60}m {s % 60}s'
    if s < 86400:    return f'{s // 3600}h {(s % 3600) // 60}m'
    return f'{s // 86400}d {(s % 86400) // 3600}h'


def render_list(listing, console: Console) -> None:
    stacks = getattr(listing, 'stacks', [])
    if not stacks:
        console.print('  [dim]No stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'   , style='bold')
    t.add_column('instance-id'  , style='dim')
    t.add_column('state'        )
    t.add_column('instance-type')
    t.add_column('public-ip'    , style='cyan')
    t.add_column('uptime'       )
    t.add_column('region'       , style='dim')
    t.add_column('pricing'      )
    for s in stacks:
        state   = str(s.state.value) if hasattr(s.state, 'value') else str(getattr(s, 'state', ''))
        pricing = ('[cyan]spot[/]' if getattr(s, 'spot', False) else '[dim]on-demand[/]') if hasattr(s, 'spot') else ''
        t.add_row(
            str(getattr(s, 'stack_name',    '')) or '—',
            str(getattr(s, 'instance_id',   '')) or '—',
            state or '—'                              ,
            str(getattr(s, 'instance_type', '')) or '—',
            str(getattr(s, 'public_ip',     '')) or '—',
            humanize_uptime(getattr(s, 'uptime_seconds', 0)),
            str(getattr(s, 'region',        '')) or '—',
            pricing                                   ,
        )
    console.print(t)


def render_info(info, console: Console) -> None:
    stack_name = str(getattr(info, 'stack_name', ''))
    instance_id = str(getattr(info, 'instance_id', ''))
    state_raw = info.state.value if hasattr(info, 'state') and hasattr(info.state, 'value') else str(getattr(info, 'state', ''))
    console.print()
    console.print(Panel(f'[bold]{stack_name}[/]  [dim]{instance_id}[/]  {state_raw}', expand=False))
    console.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16, no_wrap=True)
    t.add_column()
    for key in ('region', 'instance_type', 'disk_size_gb', 'ami_id', 'public_ip',
                'security_group_id', 'allowed_ip', 'model_name', 'api_base_url',
                'uptime_seconds', 'launch_time'):
        val = getattr(info, key, None)
        if val is None:
            continue
        if   key == 'disk_size_gb' and int(val or 0) > 0: display = f'{val} GiB'
        elif key == 'uptime_seconds':                     display = humanize_uptime(val)
        else:                                             display = str(val) or '—'
        label = 'uptime' if key == 'uptime_seconds' else key.replace('_', '-')
        t.add_row(label, display)
    if hasattr(info, 'spot'):
        t.add_row('pricing', '[cyan]spot[/]' if info.spot else '[dim]on-demand[/]')
    console.print(t)
    console.print()


def render_create(response, console: Console) -> None:
    info       = getattr(response, 'stack_info', response)
    stack_name = str(getattr(info, 'stack_name', ''))
    instance_id = str(getattr(info, 'instance_id', ''))
    elapsed    = getattr(response, 'elapsed_ms', 0)
    console.print()
    console.print(Panel(f'[bold green]Launching[/]  ·  {stack_name}', border_style='green', expand=False))
    console.print()
    console.print(f'  instance-id : [dim]{instance_id}[/]')
    console.print(f'  submitted in: {elapsed / 1000:.1f}s')
    console.print()


def render_delete(stack_name: str, deleted: bool, console: Console) -> None:
    if deleted:
        console.print(f'  [green]✓  deleted[/] {stack_name}')
    else:
        console.print(f'  [red]✗  failed to delete[/] {stack_name}')


def render_health_probe(probe, console: Console) -> None:
    healthy = getattr(probe, 'healthy', False)
    state   = getattr(probe, 'state',   '')
    elapsed = getattr(probe, 'elapsed_ms', 0)
    error   = str(getattr(probe, 'last_error', '') or '')
    if healthy:
        console.print(f'  [green]✓  healthy[/]  state={state}  ({elapsed}ms)')
    else:
        console.print(f'  [red]✗  not healthy[/]  state={state}  ({elapsed}ms)')
        if error:
            console.print(f'     [dim]{error}[/]')


def render_ami_list(listing, console: Console) -> None:
    amis = getattr(listing, 'amis', [])
    if not amis:
        console.print('  [dim]No AMIs found for this spec.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('ami-id'      , style='bold cyan')
    t.add_column('name'        )
    t.add_column('state'       )
    t.add_column('created'     , style='dim')
    t.add_column('size'        )
    t.add_column('source-stack', style='dim')
    for a in amis:
        state         = str(getattr(a, 'state', ''))
        state_styled  = (f'[green]{state}[/]'  if state == 'available'
                    else f'[yellow]{state}[/]' if state in ('pending', 'transient')
                    else f'[red]{state}[/]'    if state in ('failed', 'invalid', 'error')
                    else state or '—')
        size_gb       = int(getattr(a, 'size_gb', 0) or 0)
        t.add_row(
            str(getattr(a, 'ami_id'      , '')) or '—',
            str(getattr(a, 'name'        , '')) or '—',
            state_styled                              ,
            str(getattr(a, 'created_at'  , ''))[:19] or '—',
            f'{size_gb} GiB' if size_gb else '—'      ,
            str(getattr(a, 'source_stack', '')) or '—',
        )
    console.print(t)


def render_ami_bake(info, console: Console) -> None:
    console.print()
    console.print(Panel(f'[bold green]Baking AMI[/]  ·  {info.name}',
                        border_style='green', expand=False))
    console.print()
    console.print(f'  ami-id : [bold cyan]{info.ami_id}[/]')
    console.print(f'  state  : {info.state}  [dim](available in 5–15 min — use `ami wait`)[/]')
    if str(getattr(info, 'source_stack', '')):
        console.print(f'  source : {info.source_stack}  [dim]({info.source_instance})[/]')
    console.print()


def render_ami_delete(ami_id: str, deregistered: bool, snapshots_deleted: int,
                      console: Console) -> None:
    if deregistered:
        console.print(f'  [green]✓  deregistered[/] {ami_id}  [dim]({snapshots_deleted} snapshot(s) deleted)[/]')
    else:
        console.print(f'  [red]✗  failed to deregister[/] {ami_id}')


def render_ami_wait(ami_id: str, state: str, elapsed_sec: int, console: Console) -> None:
    if state == 'available':
        console.print(f'  [green]✓  available[/]  {ami_id}  [dim]({elapsed_sec}s)[/]')
    else:
        console.print(f'  [yellow]…  state={state or "unknown"}[/]  {ami_id}  [dim]({elapsed_sec}s)[/]')


def render_exec_result(result, console: Console) -> None:
    stdout    = str(getattr(result, 'stdout',    '') or '')
    stderr    = str(getattr(result, 'stderr',    '') or '')
    exit_code = int(getattr(result, 'exit_code', 0)  or 0)
    transport = str(getattr(result, 'transport', '') or '')
    elapsed   = int(getattr(result, 'duration_ms', 0) or 0)
    if stdout:
        console.print(stdout)
    if stderr:
        console.print(f'[yellow]{stderr}[/]', err=True)
    console.print(f'  [dim]exit={exit_code}  via={transport}  {elapsed}ms[/]')
