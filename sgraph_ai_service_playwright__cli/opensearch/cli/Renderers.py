# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch Renderers
# Tier-2A Rich-based renderers for the sp os typer commands. Pure functions
# — they accept a Type_Safe schema and write to a Console. No service calls,
# no AWS calls, no print() that the FastAPI routes would ever trigger.
# Single responsibility: schema → human-readable Rich output.
# ═══════════════════════════════════════════════════════════════════════════════

from rich.console                                                                   import Console
from rich.panel                                                                     import Panel
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Health        import Schema__OS__Health
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Response import Schema__OS__Stack__Create__Response
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Info   import Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__List   import Schema__OS__Stack__List


def _state_colour(state: Enum__OS__Stack__State) -> str:
    return {Enum__OS__Stack__State.READY      : 'green' ,
            Enum__OS__Stack__State.RUNNING    : 'green' ,
            Enum__OS__Stack__State.PENDING    : 'yellow',
            Enum__OS__Stack__State.TERMINATING: 'red'   ,
            Enum__OS__Stack__State.TERMINATED : 'red'   ,
            Enum__OS__Stack__State.UNKNOWN    : 'white' }.get(state, 'white')


def render_list(listing: Schema__OS__Stack__List, c: Console) -> None:
    if not listing.stacks:
        c.print('  [dim]No OpenSearch stacks found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('stack-name'  , style='bold')
    t.add_column('instance-id' , style='dim')
    t.add_column('state')
    t.add_column('public-ip'   , style='green')
    t.add_column('region'      , style='cyan')
    for info in listing.stacks:
        t.add_row(str(info.stack_name)                   ,
                  str(info.instance_id)                  ,
                  f'[{_state_colour(info.state)}]{info.state.value}[/]',
                  str(info.public_ip) or '—'             ,
                  str(info.region)                       )
    c.print(t)


def render_info(info: Schema__OS__Stack__Info, c: Console) -> None:
    colour = _state_colour(info.state)
    c.print()
    c.print(Panel(f'[bold]ℹ️   OpenSearch stack[/]  ·  {info.stack_name}  '
                  f'[dim]{info.instance_id}[/]  [{colour}]{info.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    t.add_row('region'       , str(info.region)         or '—')
    t.add_row('ami'          , str(info.ami_id)         or '—')
    t.add_row('public-ip'    , str(info.public_ip)      or '—')
    t.add_row('dashboards'   , str(info.dashboards_url) or '—')
    t.add_row('os-endpoint'  , str(info.os_endpoint)    or '—')
    t.add_row('allowed-ip'   , str(info.allowed_ip)     or '—')
    c.print(t)
    c.print()


def render_create(resp: Schema__OS__Stack__Create__Response, c: Console) -> None:
    c.print()
    c.print(Panel(f'[bold green]🚀  Created sp os stack[/]  ·  {resp.stack_name}', border_style='green', expand=False))
    c.print()
    c.print(f'  instance-id    : [dim]{resp.instance_id}[/]')
    c.print(f'  region         : {resp.region}')
    c.print(f'  ami            : {resp.ami_id}')
    c.print(f'  dashboards-url : {resp.dashboards_url}  [dim](self-signed TLS — accept the warning)[/]')
    c.print(f'  admin-username : {resp.admin_username}')
    c.print(f'  admin-password : [bold green]{resp.admin_password}[/]   [yellow](returned once — stash it now)[/]')
    c.print()


def render_health(h: Schema__OS__Health, c: Console) -> None:
    colour = _state_colour(h.state)
    c.print()
    c.print(Panel(f'[bold]🩺  Health  ·  {h.stack_name}[/]  [{colour}]{h.state.value}[/]',
                  border_style=colour, expand=False))
    c.print()
    rows = (('cluster-status', str(h.cluster_status) or '—'                ),
            ('node-count'    , '—' if h.node_count    < 0 else str(h.node_count   )),
            ('active-shards' , '—' if h.active_shards < 0 else str(h.active_shards)),
            ('dashboards-ok' , 'yes' if h.dashboards_ok else 'no'           ),
            ('os-endpoint-ok', 'yes' if h.os_endpoint_ok else 'no'          ),
            ('error'         , str(h.error) or '—'                          ))
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14, no_wrap=True)
    t.add_column(style='default')
    for label, value in rows:
        t.add_row(label, value)
    c.print(t)
    c.print()
