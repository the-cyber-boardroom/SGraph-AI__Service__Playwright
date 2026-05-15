# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: CLI Renderers
# Pure Rich renderers wired into the Spec__CLI__Builder via Schema__Spec__CLI__Spec.
# No AWS calls, no business logic.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Renderers__Base import humanize_time_left, humanize_uptime


def render_playwright_info(info, console: Console) -> None:
    stack_name  = str(getattr(info, 'stack_name',  ''))
    instance_id = str(getattr(info, 'instance_id', ''))
    state       = str(getattr(info, 'state', '') or '')
    console.print()
    console.print(Panel(f'[bold]{stack_name}[/]  [dim]{instance_id}[/]  {state}', expand=False))
    console.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18, no_wrap=True)
    t.add_column()

    playwright_url = str(getattr(info, 'playwright_url', '') or '')
    if playwright_url:
        t.add_row('playwright-url', f'[bold cyan]{playwright_url}[/]')

    with_mitmproxy = bool(getattr(info, 'with_mitmproxy', False))
    mode = '[green]with-mitmproxy[/] (3 containers)' if with_mitmproxy else '[dim]default[/] (2 containers)'
    t.add_row('mode', mode)

    sidecar_admin_url = str(getattr(info, 'sidecar_admin_url', '') or '')
    if sidecar_admin_url:
        t.add_row('sidecar-admin', sidecar_admin_url)

    for key, label in (('region',           'region'        ),
                       ('instance_type',    'instance-type' ),
                       ('ami_id',           'ami-id'        ),
                       ('public_ip',        'public-ip'     ),
                       ('security_group_id','security-group')):
        val = str(getattr(info, key, '') or '')
        if val:
            t.add_row(label, val)

    uptime = getattr(info, 'uptime_seconds', 0)
    if uptime:
        t.add_row('uptime', humanize_uptime(uptime))

    pricing = getattr(info, 'spot', None)
    if pricing is not None:
        t.add_row('pricing', '[cyan]spot[/]' if pricing else '[dim]on-demand[/]')

    terminate_at = str(getattr(info, 'terminate_at', '') or '')
    if terminate_at:
        remaining = int(getattr(info, 'time_remaining_sec', 0) or 0)
        t.add_row('terminate-at', terminate_at)
        t.add_row('time-left',    humanize_time_left(terminate_at, remaining))

    console.print(t)
    console.print()


def render_playwright_create(response, console: Console) -> None:
    info        = getattr(response, 'stack_info', None) or response
    stack_name  = str(getattr(info, 'stack_name',  ''))
    instance_id = str(getattr(info, 'instance_id', ''))
    playwright_url = str(getattr(info, 'playwright_url', '') or '')
    api_key     = str(getattr(response, 'api_key', '') or '')
    elapsed     = getattr(response, 'elapsed_ms', 0)

    console.print()
    console.print(Panel(f'[bold green]Launching[/]  ·  {stack_name}', border_style='green', expand=False))
    console.print()
    console.print(f'  instance-id : [dim]{instance_id}[/]')
    console.print(f'  submitted in: {elapsed / 1000:.1f}s')
    console.print()

    # The api_key is the one shared secret — it gates the sg-playwright HTTP API
    # (X-API-Key header). Shown once here; baked into the compose .env on the box.
    if api_key:
        console.print(Panel(
            f'[bold yellow]{api_key}[/]\n\n'
            f'[dim]Save this now — shown once, not recoverable from the API.[/]\n'
            f'[dim]It is the FAST_API__AUTH__API_KEY__VALUE for the sg-playwright API.[/]',
            title='[bold]api key[/]', border_style='yellow', expand=False))
        console.print()

    if playwright_url:
        console.print(f'  playwright-url : [bold cyan]{playwright_url}[/]')
    else:
        console.print('  [dim]public IP assigned shortly — run [cyan]sg playwright info[/] for the URL,[/]')
        console.print('  [dim]or [cyan]sg playwright create --wait[/] to block until healthy.[/]')
    console.print()
