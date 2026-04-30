# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox Renderers
# Tier-2A Rich renderers for sp firefox typer commands. Pure functions — accept
# a Type_Safe schema, write to a Console. No service / AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Stack__State    import Enum__Firefox__Stack__State
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Health__Response      import Schema__Firefox__Health__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Response import Schema__Firefox__Stack__Create__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Info import Schema__Firefox__Stack__Info
from sgraph_ai_service_playwright__cli.firefox.collections.List__Schema__Firefox__AMI__Info        import List__Schema__Firefox__AMI__Info
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__AMI__Create__Response      import Schema__Firefox__AMI__Create__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Set__Interceptor__Response import Schema__Firefox__Set__Interceptor__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__List import Schema__Firefox__Stack__List


def _secs(ms: int) -> str:
    return f'{ms / 1000:.1f}s'


def _fmt_uptime(seconds: int) -> str:
    if seconds <= 0:
        return '—'
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m      = rem // 60
    if d > 0:
        return f'{d}d {h}h'
    if h > 0:
        return f'{h}h {m}m'
    return f'{m}m'


def _state_colour(state: Enum__Firefox__Stack__State) -> str:
    return {Enum__Firefox__Stack__State.READY      : 'green' ,
            Enum__Firefox__Stack__State.RUNNING    : 'green' ,
            Enum__Firefox__Stack__State.PENDING    : 'yellow',
            Enum__Firefox__Stack__State.TERMINATING: 'red'   ,
            Enum__Firefox__Stack__State.TERMINATED : 'red'   ,
            Enum__Firefox__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def render_list(listing: Schema__Firefox__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No Firefox stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name' , style='bold')
    t.add_column('instance-id', style='dim')
    t.add_column('state')
    t.add_column('uptime'     , style='cyan')
    t.add_column('public-ip'  , style='green')
    t.add_column('region'     , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                                            ,
                  str(info.instance_id)                                           ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]'           ,
                  _fmt_uptime(info.uptime_seconds)                                ,
                  str(info.public_ip) or '—'                                      ,
                  str(info.region)                                                )
    c.print(t)


def render_info(info: Schema__Firefox__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]ℹ️   Firefox stack[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('region'    , str(info.region)      or '—')
    t.add_row('ami'       , str(info.ami_id)      or '—')
    t.add_row('public-ip' , str(info.public_ip)   or '—')
    t.add_row('viewer'    , str(info.viewer_url)  or '—')
    t.add_row('mitmweb'   , str(info.mitmweb_url) or '—')
    t.add_row('allowed-ip', str(info.allowed_ip)  or '—')
    t.add_row('launched'  , str(info.launch_time) or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__Firefox__Stack__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp firefox stack[/]  ·  {resp.stack_name}', border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id  : [dim]{resp.instance_id}[/]')
    c.print(f'  region       : {resp.region}')
    c.print(f'  ami          : {resp.ami_id}')
    c.print(f'  viewer-url   : https://<public-ip>/  [dim](available once booted; accept self-signed cert)[/]')
    c.print(f'  username     : user')
    c.print(f'  password     : [bold green]{resp.password}[/]   [yellow](returned once — stash it now)[/]')
    c.print(f'  mitmweb      : http://<public-ip>:8081/   [dim](mitmproxy flows UI — available once booted)[/]')
    c.print(f'  interceptor  : {resp.interceptor_label}')
    c.print(f'  submitted in : {_secs(resp.elapsed_ms)}')
    c.print()
    c.print(f'  [dim]Tip: run [bold]sp firefox info {resp.stack_name}[/] to get the public IP once running.[/]')
    c.print()


def render_health(h: Schema__Firefox__Health__Response, c: Console) -> None:
    colour = 'green' if h.healthy else _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{"healthy" if h.healthy else h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('state'      , h.state.value)
    t.add_row('firefox-ok' , '[green]yes[/]' if h.firefox_ok else '[dim]no[/]')
    t.add_row('mitmweb-ok' , '[green]yes[/]' if h.mitmweb_ok else '[dim]no[/]')
    t.add_row('waited'     , _secs(h.elapsed_ms))
    t.add_row('message'    , str(h.message) or '—')
    c.print(t)
    c.print()


def render_ami_list(amis: List__Schema__Firefox__AMI__Info, c: Console) -> None:
    if not amis:
        c.print('  [dim]No Firefox AMIs found.[/]  Run: [bold]sp firefox ami create[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('ami-id'       , style='bold')
    t.add_column('name'         , style='default')
    t.add_column('source-stack' , style='dim')
    t.add_column('state')
    t.add_column('created'      , style='dim')
    for ami in amis:
        state_colour = 'green' if str(ami.state) == 'available' else 'yellow'
        t.add_row(str(ami.ami_id)       ,
                  str(ami.name)         ,
                  str(ami.source_stack) or '—',
                  f'[{state_colour}]{ami.state}[/]',
                  str(ami.creation_date)[:19] or '—')
    c.print()
    c.print(t)
    c.print(f'\n  [dim]{len(amis)} AMI(s)[/]\n')


def render_ami_create(resp: Schema__Firefox__AMI__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]📸  AMI bake submitted[/]  ·  [bold]{resp.ami_id}[/]  [dim]{resp.ami_name}[/]',
                  border_style='green', expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('ami-id'      , str(resp.ami_id)     )
    t.add_row('name'        , str(resp.ami_name)   )
    t.add_row('source'      , str(resp.stack_name) )
    t.add_row('instance'    , str(resp.instance_id))
    t.add_row('region'      , str(resp.region)     )
    t.add_row('state'       , '[yellow]pending[/] — baking takes 5-10 min')
    t.add_row('submitted in', _secs(resp.elapsed_ms))
    c.print(t)
    c.print()
    c.print(f'  [dim]Tip: run [bold]sp firefox ami wait {resp.ami_id}[/] to poll until available.[/]')
    c.print()


def render_set_interceptor(resp: Schema__Firefox__Set__Interceptor__Response, c: Console) -> None:
    if resp.success:
        c.print()
        c.print(Panel(f'[bold green]🔌  Interceptor updated[/]  ·  {resp.stack_name}  '
                      f'[dim]{resp.instance_id}[/]  [green]{resp.interceptor_label}[/]',
                      border_style='green', expand=False))
        c.print()
        c.print(f'  [dim]{resp.message}  ({_secs(resp.elapsed_ms)})[/]')
        c.print(f'  [dim]mitmproxy reloads the script automatically — no restart needed.[/]')
        c.print()
    else:
        c.print()
        c.print(Panel(f'[bold red]✗  Interceptor update failed[/]  ·  {resp.stack_name}',
                      border_style='red', expand=False))
        c.print()
        c.print(f'  [red]{resp.message}[/]  [dim]({_secs(resp.elapsed_ms)})[/]')
        c.print()


def render_setup(info: dict, c: Console) -> None:
    ok  = info.get('role') and info.get('profile') and info.get('role_linked')
    col = 'green' if ok else 'yellow'
    c.print()
    c.print(Panel(f'[bold]IAM setup  ·  {info.get("profile_name", "")}[/]  [{col}]{"ready" if ok else "incomplete"}[/]',
                  border_style=col, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('role'       , '[green]yes[/]' if info.get('role'       ) else '[red]missing[/]')
    t.add_row('profile'    , '[green]yes[/]' if info.get('profile'    ) else '[red]missing[/]')
    t.add_row('role-linked', '[green]yes[/]' if info.get('role_linked') else '[red]missing[/]')
    c.print(t)
    c.print()
    if not ok:
        c.print('  [yellow]Run: [bold]sp firefox setup[/] to create the missing resources.[/]')
        c.print()


def render_interceptors(examples: list, c: Console) -> None:
    c.print()
    c.print(Panel('[bold]🔌  Firefox interceptor examples[/]  '
                  '[dim](pass name to --interceptor, or use --interceptor-script for custom)[/]',
                  border_style='blue', expand=False))
    c.print()
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('name'       , style='bold green')
    t.add_column('description', style='default')
    descriptions = {
        'add_cors'       : 'Add CORS headers (Access-Control-Allow-*) to every response',
        'block_trackers' : 'Block requests to common ad/tracker domains with 204',
        'cookie_logger'  : 'Print Set-Cookie headers for every response',
        'flow_recorder'  : 'Log method, URL and status code for every response',
        'header_injector': 'Inject X-Sg-Firefox-Marker header into every request',
        'header_logger'  : 'Print all request headers to the mitmproxy log',
        'request_timer'  : 'Time each request and print elapsed ms + status code',
        'response_logger': 'Log HTTP status code, method and URL for every response',
    }
    for name in examples:
        t.add_row(name, descriptions.get(name, ''))
    c.print(t)
    c.print()
    c.print('  [dim]Usage:[/]')
    c.print('    [bold]sp firefox create --interceptor header_logger[/]')
    c.print('    [bold]sp firefox create --interceptor-script ./my_interceptor.py[/]')
    c.print()
