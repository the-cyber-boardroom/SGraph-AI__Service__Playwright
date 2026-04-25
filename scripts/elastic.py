# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — elastic.py
# CLI entry-point: sp elastic   (hidden alias: sp el)
# Manage ephemeral Elasticsearch + Kibana EC2 stacks. One EC2 instance hosts
# both services (single-node ES + Kibana behind nginx-TLS on :443). Lifecycle:
# create → wait → seed → delete.
#
# This module is the thin Typer wrapper. All logic lives in Elastic__Service —
# the CLI only constructs the service, calls one method, and renders the
# result via Rich tables.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import os
import traceback
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console
from rich.markup                                                                    import escape as rich_escape
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Saved_Object__Type       import Enum__Saved_Object__Type
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Request    import Schema__Elastic__Seed__Request
from sgraph_ai_service_playwright__cli.elastic.service.AWS__Error__Translator       import AWS__Error__Translator
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service


DEBUG_TRACE = False                                                                 # Toggled by the --debug callback below; aws_error_handler reads this on each error


def humanize_uptime(seconds: int) -> str:                                            # Compact "3h 12m" / "47m" / "12s" — no calendar lib, deliberately rough
    if seconds <= 0:
        return '—'
    days,    rem = divmod(seconds, 86400)
    hours,   rem = divmod(rem,     3600)
    minutes, _   = divmod(rem,     60)
    if days:    return f'{days}d {hours}h'
    if hours:   return f'{hours}h {minutes}m'
    if minutes: return f'{minutes}m'
    return f'{seconds}s'


def fmt_ms_since(ms_value):                                                          # Render an integer ms value as "  93s  (93784 ms)" or "—" when None
    if ms_value is None:
        return '[dim]—[/]'
    return f'[bold]{ms_value // 1000:>3}s[/]  [dim]({ms_value} ms)[/]'


def render_bootstrap_stats(c, t0_ms: int, launch_ms: int, milestones_ms: dict, wait_done_ms: int,
                           seed_done_ms: int = None, seed_response = None) -> None:
    """Stats panel printed at the end of `sp el create --wait [--seed]`.
    Every value is wall-clock ms since the command was invoked.
    """
    import time as _time
    total_ms = (int(_time.monotonic() * 1000) - t0_ms)
    t = Table(show_header=False, box=None, padding=(0, 2), title='[bold]Bootstrap timeline[/]', title_justify='left')
    t.add_column(style='dim', justify='right')
    t.add_column()
    t.add_row('aws launch returned' , fmt_ms_since(launch_ms))
    t.add_row('elastic ready (y/g)' , fmt_ms_since(milestones_ms.get('es_ready')))
    t.add_row('kibana ready (200)'  , fmt_ms_since(milestones_ms.get('kibana_ready')))
    t.add_row('wait phase finished' , fmt_ms_since(wait_done_ms))
    if seed_done_ms is not None:
        t.add_row('seed finished'       , fmt_ms_since(seed_done_ms))
    t.add_row('[bold]total wall time[/]', fmt_ms_since(total_ms))
    c.print(t)
    if seed_response is not None and seed_response.documents_posted > 0:
        c.print(f'  [dim]bulk-post:[/] {seed_response.duration_ms} ms · {seed_response.docs_per_second} docs/sec · {seed_response.batches} batches')
    c.print()


app = typer.Typer(help='Ephemeral Elasticsearch + Kibana EC2 stacks (single-node, MB-scale).',
                  no_args_is_help=True)


@app.callback()
def _elastic_root(debug: bool = typer.Option(False, '--debug',
                                              help='Show the full Python traceback on errors. Off by default — friendly one-line summary only.')):
    """Manage ephemeral Elastic+Kibana stacks. Pass --debug before a sub-command to get full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def build_service() -> Elastic__Service:                                            # Single construction site so tests can swap with __In_Memory subclass
    return Elastic__Service()


def resolve_stack_name(service   : Elastic__Service ,                               # Pick a stack name when the user didn't pass one: 0 → exit, 1 → auto-use, N → prompt
                       provided  : Optional[str]    ,
                       region    : Optional[str]    ,
                       prompt_fn = None                                              # Tests inject a fake for the multi-stack branch; defaults to typer.prompt
                       ) -> str:
    if provided:
        return provided
    listing = service.list_stacks(region=region or '')
    names   = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or 'the current region'

    if len(names) == 0:
        err = Console(highlight=False, stderr=True)
        err.print(f'\n  [yellow]No elastic stacks in {region_label}.[/]  Run: [bold]sp elastic create[/]\n')
        raise typer.Exit(1)

    if len(names) == 1:
        Console(highlight=False).print(f'\n  [dim]One stack found — using [bold]{names[0]}[/][/]')
        return names[0]

    c = Console(highlight=False)
    c.print(f'\n  [bold]Multiple stacks in {region_label}:[/]')
    for idx, name in enumerate(names, start=1):
        c.print(f'    {idx}. {name}')
    if prompt_fn is None:
        prompt_fn = lambda: typer.prompt('\n  Pick a stack number', type=int)
    raw = prompt_fn()
    try:
        choice = int(raw)
    except (TypeError, ValueError):
        choice = -1
    if choice < 1 or choice > len(names):
        Console(highlight=False, stderr=True).print(f'\n  [red]Invalid selection: {raw}[/]\n')
        raise typer.Exit(1)
    return names[choice - 1]


def aws_error_handler(fn):                                                          # Wraps every command so AWS-side failures render friendly text; surprises still re-raise
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            hint    = AWS__Error__Translator().translate(exc)
            console = Console(highlight=False, stderr=True)
            console.print()
            if hint.recognised:                                                     # Known AWS-side problem class — friendly headline + hints
                console.print(f'  [red]✗[/]  [bold]{rich_escape(str(hint.headline))}[/]')
                console.print(f'     {rich_escape(str(hint.body))}')
                for action in hint.hints:                                           # AWS messages can include "[ec2.amazonaws.com]" or ARNs — escape so Rich doesn't try to parse them as markup
                    console.print(f'     [dim]›[/] {rich_escape(str(action))}')
                exit_code = int(hint.exit_code)
            else:                                                                   # Unknown — print compact type+message; full trace only with --debug
                console.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {rich_escape(str(exc))}')
                if not DEBUG_TRACE:
                    console.print('     [dim]› Re-run with [bold]sp elastic --debug ...[/] (or [bold]sp el --debug ...[/]) to see the full Python traceback.[/]')
                exit_code = 2
            if DEBUG_TRACE:                                                         # Same flag for both branches — caller asked for the trace, show it
                console.print()
                console.print('[dim]── traceback ──────────────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(exit_code)
    return wrapped


# ── create ─────────────────────────────────────────────────────────────────────

@app.command('create')
@aws_error_handler
def cmd_create(stack_name   : Optional[str] = typer.Argument (None,           help='Stack name (auto-generated if omitted: elastic-{adj}-{scientist}).'),
               region       : Optional[str] = typer.Option   (None, '--region',  help='AWS region (defaults to AWS_Config session region).'),
               instance_type: Optional[str] = typer.Option   (None, '--instance-type', help='EC2 instance type (default t3.medium).'),
               from_ami     : Optional[str] = typer.Option   (None, '--from-ami', help='AMI id (defaults to latest AL2023 via SSM).'),
               max_hours    : int           = typer.Option   (1,    '--max-hours', help='Auto-terminate after N hours. Default: 1. Pass 0 to disable.'),
               wait         : bool          = typer.Option   (False, '--wait', help='After launch, poll until Kibana is ready (~3 min).'),
               seed         : bool          = typer.Option   (False, '--seed', help='After --wait, bulk-load 10k synthetic logs + create the data view + import the default dashboard. Implies --wait.')):
    """Launch a new ephemeral Elastic+Kibana EC2 stack. Prints ELASTIC_PASSWORD once. With --wait/--seed, runs the full bootstrap in one go."""
    import time as _time
    t0_ms = int(_time.monotonic() * 1000)                                            # Wall clock start — anchors the per-milestone deltas printed at the end
    service = build_service()
    request = Schema__Elastic__Create__Request(stack_name    = stack_name    or '' ,
                                               region        = region        or '' ,
                                               instance_type = instance_type or '' ,
                                               from_ami      = from_ami      or '' ,
                                               max_hours     = max(int(max_hours), 0))
    response   = service.create(request)
    launch_ms  = int(_time.monotonic() * 1000) - t0_ms                               # AWS run_instances round-trip
    c = Console(highlight=False)
    c.print()
    c.print(f'  [bold]Stack launched[/]  [dim](state: {response.state})[/]')
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('stack-name'   , str(response.stack_name      ))
    t.add_row('aws-name'     , str(response.aws_name_tag    ))
    t.add_row('instance-id'  , str(response.instance_id     ))
    t.add_row('region'       , str(response.region          ))
    t.add_row('instance-type', str(response.instance_type   ))
    t.add_row('ami'          , str(response.ami_id          ))
    t.add_row('security-grp' , str(response.security_group_id))
    t.add_row('caller-ip'    , f'{str(response.caller_ip)}/32 (ingress on :443)')
    t.add_row('elastic-user' , str(response.elastic_username))
    t.add_row('elastic-pass' , str(response.elastic_password))
    if max_hours > 0:
        t.add_row('auto-terminate', f'{max_hours}h from boot  [dim](pass --max-hours 0 to disable)[/]')
    else:
        t.add_row('auto-terminate', '[yellow]disabled[/]  [dim](runs until you `sp elastic delete`)[/]')
    c.print(t)
    c.print()

    if seed:                                                                         # --seed implies --wait (seed needs Kibana up + responsive)
        wait = True

    if not wait:
        c.print('  [bold]Next steps[/]:')
        c.print(f'    export SG_ELASTIC_PASSWORD={str(response.elastic_password)}')
        c.print(f'    sp elastic wait {str(response.stack_name)}        [dim]# poll until Kibana is ready[/]')
        c.print(f'    sp elastic seed {str(response.stack_name)}        [dim]# bulk-load 10k synthetic log docs[/]')
        c.print()
        return

    # --wait: poll until Kibana is ready, with the same Rich spinner as `sp el wait`
    from rich.status                                                                import Status
    stack_str   = str(response.stack_name)
    pwd         = str(response.elastic_password)
    c.print(f'  [bold]Waiting for Kibana[/]  [dim](polling every 10s, up to 900s — fresh boot is ~3 min)[/]')
    wait_t0_ms     = int(_time.monotonic() * 1000)                                  # When we started polling — used to translate tick.elapsed_ms (since wait start) to wall-clock-since-create
    milestones_ms  = {'es_ready': None, 'kibana_ready': None}                       # Wall-clock ms since t0_ms
    status = Status('initialising probe...', console=c, spinner='dots')
    status.start()
    try:
        def on_tick(tick):
            secs = tick.elapsed_ms // 1000
            es_str = str(tick.elastic_probe)
            kb_str = str(tick.probe)
            wall_ms = (wait_t0_ms - t0_ms) + tick.elapsed_ms                        # tick.elapsed_ms is from wait_until_ready start; rebase to "since create"
            if es_str in ('yellow', 'green') and milestones_ms['es_ready']     is None: milestones_ms['es_ready']     = wall_ms
            if kb_str == 'ready'             and milestones_ms['kibana_ready'] is None: milestones_ms['kibana_ready'] = wall_ms
            status.update(f'[dim][{secs:>3}s  #{tick.attempt:02d}][/]  '
                          f'state=[bold]{tick.info.state}[/]  '
                          f'es=[bold]{tick.elastic_probe}[/]  '
                          f'kibana=[bold]{tick.probe}[/]  — {tick.message}')
        info = service.wait_until_ready(stack_name      = Safe_Str__Elastic__Stack__Name(stack_str),
                                        timeout         = 900                                       ,
                                        poll_seconds    = 10                                        ,
                                        elastic_password= pwd                                       ,
                                        on_progress     = on_tick                                   )
    finally:
        status.stop()
    wait_done_ms = int(_time.monotonic() * 1000) - t0_ms
    if str(info.state) != 'ready':
        c.print(f'  [red]✗[/]  Stack did not reach ready (state={info.state})  [dim]— `sp el info {stack_str}` for details[/]\n')
        raise typer.Exit(2)
    c.print(f'  [green]✓[/]  Kibana is ready at [bold]{str(info.kibana_url)}[/]\n')

    if not seed:
        render_bootstrap_stats(c, t0_ms, launch_ms, milestones_ms, wait_done_ms)
        c.print('  [bold]Next step[/]:')
        c.print(f'    export SG_ELASTIC_PASSWORD={pwd}')
        c.print(f'    sp elastic seed {stack_str}        [dim]# bulk-load 10k synthetic log docs + create the dashboard[/]\n')
        return

    # --seed: also load 10k synthetic docs, create the data view + dashboard
    c.print(f'  [bold]Seeding[/]  [dim](10000 docs, default index sg-synthetic, default dashboard)[/]')
    seed_t0_ms = int(_time.monotonic() * 1000)
    seed_request = Schema__Elastic__Seed__Request(stack_name       = Safe_Str__Elastic__Stack__Name(stack_str),
                                                   index            = 'sg-synthetic'                            ,
                                                   document_count   = 10_000                                    ,
                                                   window_days      = 7                                         ,
                                                   elastic_password = Safe_Str__Elastic__Password(pwd)          ,
                                                   batch_size       = 1_000                                     ,
                                                   create_data_view = True                                      ,
                                                   time_field_name  = 'timestamp'                               ,
                                                   create_dashboard = True                                      )
    seed_response = service.seed_stack(seed_request)
    seed_done_ms  = int(_time.monotonic() * 1000) - t0_ms
    c.print(f'  [green]✓[/]  posted [bold]{seed_response.documents_posted}[/] docs to {seed_response.index}  [dim]({seed_response.duration_ms} ms, {seed_response.docs_per_second} docs/sec)[/]')
    if str(seed_response.data_view_id):
        verb = 'created' if seed_response.data_view_created else 'reused'
        c.print(f'  [green]✓[/]  data view {verb}  [dim]id={rich_escape(str(seed_response.data_view_id))}[/]')
    if str(seed_response.dashboard_id):
        c.print(f'  [green]✓[/]  dashboard imported  [dim]"{rich_escape(str(seed_response.dashboard_title))}" ({seed_response.dashboard_objects} objects)[/]')
    c.print()
    render_bootstrap_stats(c, t0_ms, launch_ms, milestones_ms, wait_done_ms,
                            seed_done_ms=seed_done_ms, seed_response=seed_response)
    c.print('  [bold]Open Kibana[/]:')
    c.print(f'    [bold]{str(info.kibana_url)}app/dashboards[/]  [dim]# user: elastic / password above[/]')
    c.print(f'    export SG_ELASTIC_PASSWORD={pwd}\n')


@app.command('create-from-ami')
@aws_error_handler
def cmd_create_from_ami(ami_id        : str           = typer.Argument(...,         help='AMI id to launch (use `sp el ami list` to find one).'),
                         stack_name    : Optional[str] = typer.Argument(None,        help='Stack name (auto-generated if omitted).'),
                         region        : Optional[str] = typer.Option  (None, '--region'),
                         instance_type : Optional[str] = typer.Option  (None, '--instance-type'),
                         max_hours     : int           = typer.Option  (1,    '--max-hours', help='Auto-terminate after N hours. Default: 1. Pass 0 to disable.'),
                         wait          : bool          = typer.Option  (False, '--wait', help='Poll until Kibana is ready (~30-60s on a baked AMI).')):
    """Launch an EC2 stack from a pre-baked AMI. Skips the install user-data — AMI already carries docker-compose, certs, .env, and the harden script. Password is baked into the AMI; fetch it via `sp el exec STACK -- 'cat /opt/sg-elastic/.env'`."""
    import time as _time
    t0_ms   = int(_time.monotonic() * 1000)
    service = build_service()
    request = Schema__Elastic__Create__Request(stack_name    = stack_name    or '' ,
                                               region        = region        or '' ,
                                               instance_type = instance_type or '' ,
                                               from_ami      = ami_id              ,
                                               max_hours     = max(int(max_hours), 0))
    response   = service.create_from_ami(request)
    launch_ms  = int(_time.monotonic() * 1000) - t0_ms
    c = Console(highlight=False)
    c.print()
    c.print(f'  [bold]Fast-launched from AMI[/]  [dim](state: {response.state})[/]')
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('stack-name'   , str(response.stack_name      ))
    t.add_row('instance-id'  , str(response.instance_id     ))
    t.add_row('region'       , str(response.region          ))
    t.add_row('instance-type', str(response.instance_type   ))
    t.add_row('from-ami'     , str(response.ami_id          ))
    t.add_row('security-grp' , str(response.security_group_id))
    t.add_row('caller-ip'    , f'{str(response.caller_ip)}/32 (ingress on :443)')
    t.add_row('elastic-user' , 'elastic')
    t.add_row('elastic-pass' , '[dim]baked into AMI — fetch via `sp el exec`[/]')
    if max_hours > 0:
        t.add_row('auto-terminate', f'{max_hours}h from boot  [dim](pass --max-hours 0 to disable)[/]')
    else:
        t.add_row('auto-terminate', '[yellow]disabled[/]')
    c.print(t)
    c.print()
    c.print('  [bold]Get the elastic password[/]:')
    c.print(f'    sp el exec {str(response.stack_name)} -- "grep ELASTIC_PASSWORD /opt/sg-elastic/.env"')
    c.print()

    if not wait:
        c.print('  [bold]Next steps[/]:')
        c.print(f'    sp elastic wait {str(response.stack_name)}        [dim]# typically 30-60s on a baked AMI[/]\n')
        return

    from rich.status                                                                import Status
    stack_str   = str(response.stack_name)
    c.print(f'  [bold]Waiting for Kibana[/]  [dim](polling every 5s, up to 300s — baked AMIs typically come up in 30-60s)[/]')
    milestones_ms = {'es_ready': None, 'kibana_ready': None}
    wait_t0_ms    = int(_time.monotonic() * 1000)
    status = Status('initialising probe...', console=c, spinner='dots')
    status.start()
    try:
        def on_tick(tick):
            secs    = tick.elapsed_ms // 1000
            es_str  = str(tick.elastic_probe)
            kb_str  = str(tick.probe)
            wall_ms = (wait_t0_ms - t0_ms) + tick.elapsed_ms
            if es_str in ('yellow', 'green') and milestones_ms['es_ready']     is None: milestones_ms['es_ready']     = wall_ms
            if kb_str == 'ready'             and milestones_ms['kibana_ready'] is None: milestones_ms['kibana_ready'] = wall_ms
            status.update(f'[dim][{secs:>3}s  #{tick.attempt:02d}][/]  '
                          f'state=[bold]{tick.info.state}[/]  '
                          f'es=[bold]{tick.elastic_probe}[/]  '
                          f'kibana=[bold]{tick.probe}[/]  — {tick.message}')
        info = service.wait_until_ready(stack_name      = Safe_Str__Elastic__Stack__Name(stack_str),
                                        timeout         = 300                                       ,  # AMIs reuse on-disk state — much faster than fresh install
                                        poll_seconds    = 5                                         ,
                                        on_progress     = on_tick                                   )
    finally:
        status.stop()
    wait_done_ms = int(_time.monotonic() * 1000) - t0_ms
    if str(info.state) != 'ready':
        c.print(f'  [red]✗[/]  Stack did not reach ready (state={info.state})  [dim]— `sp el info {stack_str}` for details[/]\n')
        raise typer.Exit(2)
    c.print(f'  [green]✓[/]  Kibana is ready at [bold]{str(info.kibana_url)}[/]\n')
    render_bootstrap_stats(c, t0_ms, launch_ms, milestones_ms, wait_done_ms)


# ── list ───────────────────────────────────────────────────────────────────────

@app.command('list')
@aws_error_handler
def cmd_list(region: Optional[str] = typer.Option(None, '--region')):
    """List ephemeral elastic stacks in a region."""
    service = build_service()
    response = service.list_stacks(region=region or '')
    c = Console(highlight=False)
    if len(response.stacks) == 0:
        c.print(f'\n  [dim]No elastic stacks in {str(response.region)}.[/]  Run: [bold]sp elastic create[/]\n')
        return
    t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    t.add_column('Stack',        style='bold')
    t.add_column('Instance')
    t.add_column('State')
    t.add_column('Uptime')
    t.add_column('Public IP')
    t.add_column('Kibana URL', style='dim')
    for info in response.stacks:
        t.add_row(str(info.stack_name)   ,
                  str(info.instance_id)  ,
                  str(info.state)        ,
                  humanize_uptime(int(info.uptime_seconds)),
                  str(info.public_ip) or '—',
                  str(info.kibana_url) or '—')
    c.print()
    c.print(t)
    c.print(f'\n  [dim]region: {str(response.region)} — {len(response.stacks)} stack(s)[/]\n')


# ── info ───────────────────────────────────────────────────────────────────────

@app.command('info')
@aws_error_handler
def cmd_info(stack_name: Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             region    : Optional[str] = typer.Option  (None, '--region')):
    """Show full details for a single stack. Does NOT include the elastic password."""
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    info    = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                     region     = region or '')
    c = Console(highlight=False)
    c.print()
    c.print(f'  [bold]Stack:[/] {str(info.stack_name)}  [dim](state: {info.state})[/]')
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('aws-name'     , str(info.aws_name_tag    ) or '—')
    t.add_row('instance-id'  , str(info.instance_id     ) or '—')
    t.add_row('region'       , str(info.region          ) or '—')
    t.add_row('instance-type', str(info.instance_type   ) or '—')
    t.add_row('ami'          , str(info.ami_id          ) or '—')
    t.add_row('security-grp' , str(info.security_group_id) or '—')
    t.add_row('allowed-ip'   , f'{str(info.allowed_ip)}/32' if str(info.allowed_ip) else '—')
    t.add_row('public-ip'    , str(info.public_ip       ) or '—')
    t.add_row('kibana-url'   , str(info.kibana_url      ) or '—')
    t.add_row('launched'     , str(info.launch_time     ) or '—')
    t.add_row('uptime'       , humanize_uptime(int(info.uptime_seconds)))
    c.print(t)
    c.print()


# ── wait ───────────────────────────────────────────────────────────────────────

@app.command('wait')
@aws_error_handler
def cmd_wait(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             timeout    : int           = typer.Option (600, '--timeout', help='Max total wait in seconds. Polling interval is --poll-seconds.'),
             poll_seconds: int          = typer.Option (10, '--poll-seconds', help='Seconds between polls (default 10).'),
             region     : Optional[str] = typer.Option (None, '--region')):
    """Poll until Kibana returns HTTP 200. Live status: connection / nginx / Kibana."""
    from rich.status                                                                import Status
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    c          = Console(highlight=False)
    c.print(f'\n  [bold]Waiting for stack[/] [cyan]{stack_name}[/]  '
            f'[dim](polling every {poll_seconds}s, up to {timeout}s total)[/]')

    milestones   = {'first_running'        : None,                                  # EC2 instance enters "running"
                    'first_elastic_ready'  : None,                                  # ES /_cluster/health returns yellow|green — can start indexing here
                    'first_upstream_down'  : None,                                  # nginx answers but Kibana container still booting (502/503)
                    'first_booting'        : None,                                  # Kibana answered but not 200 yet
                    'first_ready'          : None}                                  # Kibana /api/status 200
    tick_count   = {'n': 0}

    status = Status('initialising probe...', console=c, spinner='dots')
    status.start()
    try:
        def on_tick(tick):
            tick_count['n'] = tick.attempt
            state_str       = str(tick.info.state)
            probe_str       = str(tick.probe)
            es_probe_str    = str(tick.elastic_probe)
            if state_str    == 'running'        and milestones['first_running']       is None: milestones['first_running']       = tick.elapsed_ms
            if es_probe_str in ('yellow', 'green') and milestones['first_elastic_ready'] is None:
                milestones['first_elastic_ready'] = tick.elapsed_ms
            if probe_str    == 'upstream-down'  and milestones['first_upstream_down'] is None: milestones['first_upstream_down'] = tick.elapsed_ms
            if probe_str    == 'booting'        and milestones['first_booting']       is None: milestones['first_booting']       = tick.elapsed_ms
            if probe_str    == 'ready'          and milestones['first_ready']         is None: milestones['first_ready']         = tick.elapsed_ms
            ip      = str(tick.info.public_ip) or '—'
            secs    = tick.elapsed_ms // 1000
            status.update(f'[dim][{secs:>3}s  #{tick.attempt:02d}][/]  '
                          f'state=[bold]{state_str}[/]  ip={ip}  '
                          f'es=[bold]{es_probe_str}[/]  '
                          f'kibana=[bold]{probe_str}[/]  — {tick.message}')
        info = service.wait_until_ready(stack_name      = Safe_Str__Elastic__Stack__Name(stack_name),
                                        region          = region or ''                              ,
                                        timeout         = timeout                                   ,
                                        poll_seconds    = poll_seconds                              ,
                                        elastic_password= os.environ.get('SG_ELASTIC_PASSWORD', '') ,
                                        on_progress     = on_tick                                   )
    finally:
        status.stop()

    def fmt_ms(ms):                                                                 # "—" when the milestone was never reached within the wait window
        if ms is None:
            return '[dim]—[/]'
        secs = ms // 1000
        return f'[bold]{secs:>3}s[/]  [dim]({ms} ms)[/]'

    if str(info.state) == 'ready':
        c.print(f'  ✅  Kibana is ready at [bold]{str(info.kibana_url)}[/]')
    else:
        c.print(f'  ❌  Stack {stack_name} not ready (state: {info.state})  '
                f'[dim]— re-run `sp elastic wait` or `sp elastic info` for details[/]')

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column()
    t.add_row('state → running'        , fmt_ms(milestones['first_running']       ))
    t.add_row('elastic ready (y/g)'    , fmt_ms(milestones['first_elastic_ready'] ))
    t.add_row('nginx up (502/503)'     , fmt_ms(milestones['first_upstream_down'] ))
    t.add_row('kibana booting (<200)'  , fmt_ms(milestones['first_booting']       ))
    t.add_row('kibana ready (200)'     , fmt_ms(milestones['first_ready']         ))
    t.add_row('total polls / time'     , f'[bold]{tick_count["n"]}[/] polls over [bold]{info.state}[/] — see above')
    c.print()
    c.print(t)
    c.print()


# ── health ─────────────────────────────────────────────────────────────────────

@app.command('health')
@aws_error_handler
def cmd_health(stack_name: Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
               password  : Optional[str] = typer.Option  (None, '--password', help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
               check_ssm : bool          = typer.Option  (True, '--ssm/--no-ssm', help='Run SSM-side checks (boot status + docker ps). Default on.')):
    """Diagnose a stack: EC2 state, SG ingress vs current IP, TCP :443, Elastic + Kibana probes, plus SSM-side boot status and `docker ps`."""
    service     = build_service()
    stack_name  = resolve_stack_name(service, stack_name, None)
    response    = service.health(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                  password   = password or ''                            ,
                                  check_ssm  = check_ssm                                  )

    icon_for = {'ok': '[green]✓[/]', 'warn': '[yellow]⚠[/]', 'fail': '[red]✗[/]', 'skip': '[dim]·[/]'}
    c = Console(highlight=False)
    has_warn    = any(str(chk.status) == 'warn' for chk in response.checks)         # WARN never fails the rollup (yellow on single-node is normal) but should still surface as ⚠ not ✓
    rollup_icon = '[red]✗[/]' if not response.all_ok else ('[yellow]⚠[/]' if has_warn else '[green]✓[/]')
    c.print(f'\n  {rollup_icon}  Health for [bold]{stack_name}[/]  [dim](pass --no-ssm to skip the SSM checks)[/]\n')
    t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    t.add_column('', width=2)
    t.add_column('Check')
    t.add_column('Detail', style='dim')
    for chk in response.checks:
        t.add_row(icon_for.get(str(chk.status), '·'), str(chk.name), rich_escape(str(chk.detail)))
    c.print(t)

    if not response.all_ok:                                                          # When something failed, print a targeted next-step hint based on the worst check
        sg_fail   = any(str(chk.name) == 'sg-ingress' and str(chk.status) == 'fail' for chk in response.checks)
        tcp_fail  = any(str(chk.name) == 'tcp-443'    and str(chk.status) == 'fail' for chk in response.checks)
        auth_fail = any(str(chk.name) == 'elastic'    and str(chk.status) == 'fail' and 'SG_ELASTIC_PASSWORD' in str(chk.detail) for chk in response.checks)
        c.print()
        if sg_fail or tcp_fail:
            c.print('  [yellow]Likely fix:[/] your public IP rotated since `sp el create`. Recreate the stack so the SG ingress matches your current IP, or update the SG manually.')
        if auth_fail:
            c.print('  [yellow]Likely fix:[/] re-export SG_ELASTIC_PASSWORD with the value from the most recent `sp el create` output.')
    c.print()


# ── delete ─────────────────────────────────────────────────────────────────────

@app.command('delete')
@aws_error_handler
def cmd_delete(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple. Ignored when --all is set.'),
               region     : Optional[str] = typer.Option (None, '--region'),
               all_stacks : bool          = typer.Option (False, '--all', help='Terminate every elastic stack in the region.'),
               yes        : bool          = typer.Option (False, '--yes', '-y', help='Skip the y/N confirmation prompt.')):
    """Terminate the EC2 instance and best-effort delete its security group. With --all, terminates every elastic stack in the region."""
    service = build_service()
    c       = Console(highlight=False)

    if all_stacks:
        listing    = service.list_stacks(region=region or '')
        names      = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
        region_str = str(listing.region)
        if not names:
            c.print(f'\n  [dim]No elastic stacks in {region_str}.[/]\n')
            return
        c.print(f'\n  [bold]About to delete {len(names)} stack(s) in {region_str}:[/]')
        for n in names:
            c.print(f'    [red]✗[/] {n}')
        if not yes:
            if not typer.confirm('\n  Proceed?', default=False):
                c.print('  [dim]aborted[/]\n')
                raise typer.Exit(0)
        c.print()
        deleted_count = 0
        for n in names:
            response = service.delete_stack(stack_name = Safe_Str__Elastic__Stack__Name(n),
                                            region     = region or '')
            if len(response.terminated_instance_ids) > 0:
                c.print(f'  [green]✓[/] terminated [bold]{n}[/]  [dim](instance {str(response.target)}, sg-deleted: {response.security_group_deleted})[/]')
                deleted_count += 1
            else:
                c.print(f'  [yellow]·[/] skipped [bold]{n}[/]  [dim](no instance found — may already be terminating)[/]')
        c.print(f'\n  [bold]Done — {deleted_count} stack(s) terminated.[/]\n')
        return

    stack_name = resolve_stack_name(service, stack_name, region)
    response = service.delete_stack(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                    region     = region or '')
    if len(response.terminated_instance_ids) == 0:
        c.print(f'\n  [yellow]No such stack:[/] {stack_name}\n')
        return
    c.print(f'\n  ✅  Terminated [bold]{stack_name}[/] — instance {str(response.target)}'
            f'  [dim](sg-deleted: {response.security_group_deleted})[/]\n')


# ── seed ───────────────────────────────────────────────────────────────────────

@app.command('connect')
@aws_error_handler
def cmd_connect(stack_name: Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                region    : Optional[str] = typer.Option (None, '--region')):
    """Open an interactive SSM shell on the EC2 host (no SSH/key-pair needed)."""
    import os
    import shutil
    import subprocess
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    info       = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                        region     = region or '')
    c = Console(highlight=False)
    if not str(info.instance_id):
        c.print(f'\n  [yellow]No such stack:[/] {stack_name}\n')
        raise typer.Exit(1)

    plugin_path = (shutil.which('session-manager-plugin') or
                   '/usr/local/sessionmanagerplugin/bin/session-manager-plugin')
    if not os.path.isfile(plugin_path):
        c.print('\n  [red]✗  session-manager-plugin not found in PATH.[/]')
        c.print('  Fix with one of:')
        c.print('    [bold]sudo ln -s /usr/local/sessionmanagerplugin/bin/session-manager-plugin /usr/local/bin/session-manager-plugin[/]')
        c.print('    [bold]brew install --cask session-manager-plugin[/]\n')
        raise typer.Exit(1)

    c.print(f'\n  🔌  Opening SSM session → [bold]{stack_name}[/] [dim]({info.instance_id})[/]\n')
    args = ['aws', 'ssm', 'start-session', '--target', str(info.instance_id)]
    if str(info.region):
        args += ['--region', str(info.region)]
    result = subprocess.run(args, check=False, capture_output=False)
    if result.returncode != 0:
        c.print(f'\n  [red]✗  Session ended with code {result.returncode}.[/]')
        c.print('  [dim]If you saw "Standard_Stream not found", run: brew reinstall --cask session-manager-plugin[/]\n')


@app.command('exec', context_settings={'allow_extra_args': True, 'ignore_unknown_options': True})
@aws_error_handler
def cmd_exec(ctx        : typer.Context                                                       ,
             first      : str           = typer.Argument(...,  help='Stack name OR start of the shell command (when only one stack exists).'),
             cmd        : Optional[str] = typer.Option(None, '--cmd',                          help='Shell command (alternative to positional).'),
             region     : Optional[str] = typer.Option(None, '--region')                      ,
             timeout    : int           = typer.Option(60,   '--timeout',                      help='Seconds to wait for the command to complete (min 30).')):
    """Run a shell command on the EC2 host via SSM and print stdout/stderr.

    Usage:
      sp elastic exec "docker ps"                   # auto-pick stack, run command
      sp elastic exec elastic-foo "docker ps"       # explicit stack + command
      sp elastic exec --cmd "uptime"                # auto-pick stack, command via flag
    """
    import shlex
    extra   = ctx.args or []
    service = build_service()
    listing = service.list_stacks(region=region or '')
    names   = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]

    if cmd is not None:                                                             # --cmd supplied → first is the stack name (or empty for auto-pick)
        stack_name = first if first else None
        shell_cmd  = cmd
    elif extra:                                                                     # positional command after first; first might be a stack name OR command word
        if first in names:
            stack_name = first
            shell_cmd  = shlex.join(extra)
        else:
            stack_name = None
            shell_cmd  = shlex.join([first] + extra)
    else:                                                                           # only `first` — treat as command, auto-pick stack
        stack_name = None
        shell_cmd  = first

    stack_name = resolve_stack_name(service, stack_name, region)
    if not shell_cmd:
        raise typer.BadParameter('Provide a shell command.')

    c = Console(highlight=False)
    c.print(f'\n  💻  [bold]{stack_name}[/]  [dim]$ {shell_cmd}[/]')
    result = service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                     command    = shell_cmd                                  ,
                                     region     = region or ''                               ,
                                     timeout    = timeout                                    )
    if str(result.stdout).strip():
        print(str(result.stdout).rstrip())
    if str(result.stderr).strip():
        import sys as _sys
        print(str(result.stderr).rstrip(), file=_sys.stderr)
    if not str(result.stdout).strip() and not str(result.stderr).strip():
        c.print('  [dim](no output)[/]')
    c.print(f'  [dim]→ status={result.status}  exit={result.exit_code}  duration={result.duration_ms}ms[/]\n')


@app.command('harden')
@aws_error_handler
def cmd_harden(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
               password   : Optional[str] = typer.Option  (None, '--password', help='Elastic password (else $SG_ELASTIC_PASSWORD).')):
    """Hide unused Kibana solution groups (Observability, Security, Fleet, ML, Maps, ...) from the side-nav. Stacks created on or after 2026-04-25 do this at boot — this command is a fallback for older AMIs or for re-applying. Idempotent."""
    if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
        c = Console(highlight=False)
        c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set. Pass --password or export it first.\n')
        raise typer.Exit(1)
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, None)
    result     = service.harden_kibana(stack_name=Safe_Str__Elastic__Stack__Name(stack_name),
                                        password=password or '')
    c = Console(highlight=False)
    c.print()
    if result['ok']:
        c.print(f'  [green]✓[/]  Side-nav hardened on [bold]{stack_name}[/]  [dim](Observability + Security + Fleet + ML + Maps disabled in default space)[/]')
        c.print(f'     [dim]Refresh Kibana in your browser to see the slimmer nav.[/]')
    else:
        c.print(f'  [red]✗[/]  Failed: HTTP {result["http_status"]} — {rich_escape(str(result["error"]))}')
    c.print()


@app.command('wipe')
@aws_error_handler
def cmd_wipe(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             index      : str           = typer.Option  ('sg-synthetic', '--index', help='Index name to delete (also the data view title).'),
             password   : Optional[str] = typer.Option  (None, '--password', help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
             yes        : bool          = typer.Option  (False, '--yes', '-y', help='Skip the y/N confirmation prompt.')):
    """Delete the seed-data: drop the Elastic index AND remove its Kibana data view. Idempotent — does nothing if neither exists."""
    if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
        c = Console(highlight=False)
        c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.')
        c.print('     [dim]Re-export it from the most recent `sp elastic create` output, or pass --password.[/]\n')
        raise typer.Exit(1)
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, None)
    if not yes:                                                                      # Confirm before destructive — typer.confirm exits cleanly on ^C / N
        if not typer.confirm(f'  Delete index {index!r} and its data view from {stack_name}?', default=False):
            Console(highlight=False).print('  [dim]aborted[/]\n')
            raise typer.Exit(0)
    result = service.wipe_seed(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                index      = index                                     ,
                                password   = password or ''                             )
    c = Console(highlight=False)
    c.print()
    def render_row(label, deleted, status, err):
        if err:
            return f'  [red]✗[/]  {label}: HTTP {status} — {rich_escape(str(err))}'
        if deleted:
            return f'  [green]✓[/]  {label}: deleted'
        return f'  [dim]·[/]  {label}: did not exist'
    c.print(render_row('index     ', result['index_deleted']    , result['index_status']    , result['index_error']))
    c.print(render_row('data view ', result['data_view_deleted'], result['data_view_status'], result['data_view_error']))
    dash_count = int(result.get('dashboard_objects_deleted', 0))
    if dash_count > 0:
        c.print(f'  [green]✓[/]  dashboard : {dash_count} saved object(s) deleted')
    else:
        c.print(f'  [dim]·[/]  dashboard : nothing to clean')
    c.print()


@app.command('seed')
@aws_error_handler
def cmd_seed(stack_name      : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             docs            : int           = typer.Option  (10_000, '--docs',        help='Document count (default 10000).'),
             index           : str           = typer.Option  ('sg-synthetic', '--index'),
             window_days     : int           = typer.Option  (7,    '--window-days',  help='Spread timestamps over the last N days.'),
             batch_size      : int           = typer.Option  (1_000,'--batch-size'),
             password        : Optional[str] = typer.Option  (None, '--password',     help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
             create_data_view: bool          = typer.Option  (True, '--data-view/--no-data-view', help='After bulk-post, ensure a Kibana data view points at the index. Default on — bypasses the "Now create a data view" wall in Discover.'),
             time_field      : str           = typer.Option  ('timestamp', '--time-field', help='Time field name the data view uses for time-based filtering.'),
             create_dashboard: bool          = typer.Option  (True, '--dashboard/--no-dashboard', help='After data view, also import the default 4-panel "Synthetic Logs Overview" dashboard.')):
    """Generate and bulk-post synthetic log documents to the stack's Elastic. Also creates a Kibana data view AND a default dashboard by default."""
    if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):                  # Fail fast before any AWS/HTTP work — the most common seed mistake is forgetting to export the password printed by `sp elastic create`
        c = Console(highlight=False)
        c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.')
        c.print('     [dim]Re-export it from the most recent `sp elastic create` output, e.g.:[/]')
        c.print('     [bold]export SG_ELASTIC_PASSWORD=<password-from-create>[/]')
        c.print('     [dim]Or pass it explicitly via --password.[/]\n')
        raise typer.Exit(1)
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, None)
    request = Schema__Elastic__Seed__Request(stack_name       = Safe_Str__Elastic__Stack__Name(stack_name),
                                             index            = index                                     ,
                                             document_count   = docs                                      ,
                                             window_days      = window_days                               ,
                                             elastic_password = Safe_Str__Elastic__Password(password) if password else Safe_Str__Elastic__Password(''),
                                             batch_size       = batch_size                                ,
                                             create_data_view = create_data_view                          ,
                                             time_field_name  = time_field                                ,
                                             create_dashboard = create_dashboard                          )
    response = service.seed_stack(request)
    c = Console(highlight=False)
    if response.documents_posted == 0 and response.documents_failed == 0:
        c.print(f'\n  [yellow]Nothing seeded — stack has no public IP yet:[/] {stack_name}\n')
        return
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('stack',       str(response.stack_name      ))
    t.add_row('index',       str(response.index           ))
    t.add_row('posted',      str(response.documents_posted))
    t.add_row('failed',      str(response.documents_failed))
    t.add_row('batches',     str(response.batches         ))
    t.add_row('duration',    f'{response.duration_ms} ms')
    t.add_row('rate',        f'{response.docs_per_second} docs/sec')
    t.add_row('http status', str(response.last_http_status))
    if create_data_view:
        if str(response.data_view_error):
            t.add_row('data view',   f'[yellow]not created[/]  [dim]({rich_escape(str(response.data_view_error))})[/]')
        elif str(response.data_view_id):
            verb = 'created' if response.data_view_created else 'already existed'
            t.add_row('data view',   f'[green]{verb}[/]  [dim]id={rich_escape(str(response.data_view_id))}[/]')
        else:
            t.add_row('data view',   '[dim]skipped (no docs posted)[/]')
    if create_dashboard:
        if str(response.dashboard_error):
            t.add_row('dashboard',   f'[yellow]not imported[/]  [dim]({rich_escape(str(response.dashboard_error))})[/]')
        elif str(response.dashboard_id):
            t.add_row('dashboard',   f'[green]{response.dashboard_objects} objects imported[/]  [dim]"{rich_escape(str(response.dashboard_title))}"[/]')
        else:
            t.add_row('dashboard',   '[dim]skipped (data view missing)[/]')
    c.print(t)
    if response.documents_failed > 0:                                               # Surface the WHY so the user isn't guessing (previously swallowed silently)
        c.print()
        c.print(f'  [red]✗  {response.documents_failed} of {response.documents_failed + response.documents_posted} docs rejected.[/]')
        if str(response.last_error_message):                                        # Body can contain "for REST request [/_bulk]" — escape so Rich doesn't read [/...] as a closing markup tag
            c.print(f'     [dim]first error:[/] {rich_escape(str(response.last_error_message))}')
        if response.last_http_status == 401 or response.last_http_status == 403:
            c.print('     [dim]› This is almost always SG_ELASTIC_PASSWORD not matching the live stack.[/]')
            c.print('     [dim]› Re-export with the password from the most recent `sp elastic create` output.[/]')
    c.print()


# ── ami (snapshot management) ─────────────────────────────────────────────────
#
# AMIs are created from a running stack via `sp el ami create`. They're tagged
# sg:purpose=elastic so list/delete only touch our own images. Snapshots
# behind each AMI are cleaned up on delete (AWS retains them by default).

ami_app = typer.Typer(help='Manage ephemeral elastic AMIs (list / create / delete).', no_args_is_help=True)


@ami_app.command('list')
@aws_error_handler
def cmd_ami_list(region: Optional[str] = typer.Option(None, '--region')):
    """List elastic AMIs in a region."""
    service = build_service()
    amis    = service.list_amis(region=region or '')
    c = Console(highlight=False)
    if len(amis) == 0:
        c.print(f'\n  [dim]No elastic AMIs in {region or "this region"}.[/]  Run: [bold]sp el ami create[/]\n')
        return
    t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    t.add_column('AMI id'        , style='bold')
    t.add_column('Name')
    t.add_column('Source stack'  , style='dim')
    t.add_column('State')
    t.add_column('Created'        , style='dim')
    for ami in amis:
        t.add_row(str(ami.ami_id),
                  rich_escape(str(ami.name)),
                  str(ami.source_stack) or '—',
                  str(ami.state),
                  str(ami.creation_date))
    c.print()
    c.print(t)
    c.print(f'\n  [dim]{len(amis)} AMI(s)[/]\n')


@ami_app.command('create')
@aws_error_handler
def cmd_ami_create(stack_name : Optional[str] = typer.Argument(None, help='Stack name to bake. Auto-picks when only one stack exists; prompts on multiple.'),
                   ami_name   : Optional[str] = typer.Option  (None, '--name', help='AMI Name tag (defaults to sg-elastic-ami-<stack>-<unix-ts>).'),
                   reboot     : bool          = typer.Option  (False, '--reboot/--no-reboot', help='Reboot the instance during AMI creation. Default: no-reboot (safer; ES has restart=unless-stopped, journal-replay handles in-flight writes).')):
    """Bake the running stack's EBS volume into an AMI tagged sg:purpose=elastic. Snapshots inherit the same tags. Returns the AMI id; AWS marks it pending — `sp el ami list` shows when it's available."""
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, None)
    result     = service.create_ami_from_stack(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                                ami_name   = ami_name or ''                            ,
                                                no_reboot  = not reboot                                )
    c = Console(highlight=False)
    c.print()
    if result['error']:
        c.print(f'  [red]✗[/]  AMI creation failed: {rich_escape(str(result["error"]))}\n')
        raise typer.Exit(2)
    c.print(f'  [green]✓[/]  Started AMI bake from [bold]{stack_name}[/]')
    c.print(f'     [dim]instance:[/] {result["instance_id"]}')
    c.print(f'     [dim]ami-id:  [/] [bold]{result["ami_id"]}[/]')
    c.print(f'     [dim]Track progress: `sp el ami list` (state moves pending → available; usually 5-10 min for a single-volume EBS).[/]\n')


@ami_app.command('delete')
@aws_error_handler
def cmd_ami_delete(ami_id : str  = typer.Argument(...,           help='AMI id to deregister (and delete its EBS snapshots).'),
                   region : Optional[str] = typer.Option(None, '--region'),
                   yes    : bool = typer.Option(False, '--yes', '-y', help='Skip the y/N confirmation.')):
    """Deregister an AMI and delete the EBS snapshots behind it. AWS keeps snapshots when you only deregister — this command cleans both so you don't pay for orphaned storage."""
    if not yes:
        if not typer.confirm(f'  Deregister {ami_id} and delete its snapshots?', default=False):
            Console(highlight=False).print('  [dim]aborted[/]\n')
            raise typer.Exit(0)
    service = build_service()
    result  = service.delete_ami(ami_id=ami_id, region=region or '')
    c = Console(highlight=False)
    c.print()
    if result['deregistered']:
        c.print(f'  [green]✓[/]  Deregistered [bold]{ami_id}[/]  [dim]({result["snapshots_deleted"]} snapshot(s) deleted)[/]\n')
    else:
        c.print(f'  [yellow]·[/]  No such AMI: {ami_id}\n')


app.add_typer(ami_app, name='ami')


# ── dashboard / data-view (Kibana saved objects) ───────────────────────────────
#
# Both sub-apps share the same plumbing — list / export / import — only the
# saved-object type differs (`dashboard` vs `index-pattern`). We define one
# pair of helper functions and bind them to two Typer sub-apps so the wire
# format stays identical from the user's POV.

def require_password(password: Optional[str]) -> None:                              # Same pre-flight as cmd_seed; abort early so users don't get cryptic 401s
    if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
        c = Console(highlight=False)
        c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.')
        c.print('     [dim]Re-export it from the most recent `sp elastic create` output, or pass --password.[/]\n')
        raise typer.Exit(1)


def render_auth_hint(c: Console, status: int) -> None:                              # Common 401/403 hint shared by all dashboard/data-view paths
    if status == 401 or status == 403:
        c.print('     [dim]› SG_ELASTIC_PASSWORD does not match the live stack — re-export from the most recent `sp elastic create`.[/]')


def saved_objects_list_cmd(label: str, object_type: Enum__Saved_Object__Type,
                           stack_name: Optional[str], password: Optional[str], page_size: int):
    require_password(password)
    service     = build_service()
    stack_name  = resolve_stack_name(service, stack_name, None)
    response    = service.saved_objects_find(stack_name  = Safe_Str__Elastic__Stack__Name(stack_name),
                                             object_type = object_type                                ,
                                             password    = password or ''                             ,
                                             page_size   = page_size                                  )
    c = Console(highlight=False)
    if str(response.error):
        c.print(f'\n  [red]✗  {label} list failed[/]  [dim](http {response.http_status})[/]')
        c.print(f'     [dim]{rich_escape(str(response.error))}[/]')                 # Kibana error bodies can contain bracketed text; escape so Rich doesn't crash on it
        render_auth_hint(c, response.http_status)
        c.print()
        raise typer.Exit(2)
    if response.total == 0:
        c.print(f'\n  [dim]No {label}s in {stack_name}.[/]\n')
        return
    t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    t.add_column('Title', style='bold')
    t.add_column('ID',    style='dim')
    t.add_column('Updated')
    for obj in response.objects:                                                    # Title is user-supplied (dashboard name) and may contain brackets — Table cells render with markup by default, so escape
        t.add_row(rich_escape(str(obj.title)) or '—', str(obj.id), str(obj.updated_at))
    c.print()
    c.print(t)
    c.print(f'\n  [dim]{response.total} {label}(s) in {stack_name}[/]\n')


def saved_objects_export_cmd(label: str, object_type: Enum__Saved_Object__Type,
                             stack_name: Optional[str], password: Optional[str], output: str,
                             include_references_deep: bool):
    require_password(password)
    service     = build_service()
    stack_name  = resolve_stack_name(service, stack_name, None)
    response    = service.saved_objects_export(stack_name              = Safe_Str__Elastic__Stack__Name(stack_name),
                                                object_type             = object_type                               ,
                                                output_path             = output                                    ,
                                                password                = password or ''                            ,
                                                include_references_deep = include_references_deep                   )
    c = Console(highlight=False)
    if str(response.error):
        c.print(f'\n  [red]✗  {label} export failed[/]  [dim](http {response.http_status})[/]')
        c.print(f'     [dim]{rich_escape(str(response.error))}[/]')
        render_auth_hint(c, response.http_status)
        c.print()
        raise typer.Exit(2)
    c.print(f'\n  ✅  Exported [bold]{response.object_count}[/] {label}(s) from [bold]{stack_name}[/]')
    c.print(f'     [dim]→ {rich_escape(str(response.file_path))}  ({response.bytes_written} bytes)[/]\n')


def saved_objects_import_cmd(label: str, stack_name: Optional[str], password: Optional[str],
                             input_path: str, overwrite: bool):
    require_password(password)
    if not os.path.isfile(input_path):                                              # Fail fast — Kibana would return a confusing error for an empty body
        Console(highlight=False, stderr=True).print(f'\n  [red]✗  No such file: {input_path}[/]\n')
        raise typer.Exit(1)
    service     = build_service()
    stack_name  = resolve_stack_name(service, stack_name, None)
    response    = service.saved_objects_import(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                                input_path = input_path                                 ,
                                                password   = password or ''                             ,
                                                overwrite  = overwrite                                  )
    c = Console(highlight=False)
    if not response.success and response.error_count == 0 and str(response.first_error):
        c.print(f'\n  [red]✗  {label} import failed[/]  [dim](http {response.http_status})[/]')
        c.print(f'     [dim]{rich_escape(str(response.first_error))}[/]')
        render_auth_hint(c, response.http_status)
        c.print()
        raise typer.Exit(2)
    icon = '✅' if response.success else '⚠'
    c.print(f'\n  {icon}  Imported [bold]{response.success_count}[/] {label}(s) into [bold]{stack_name}[/]'
            f'  [dim](errors: {response.error_count}, http {response.http_status})[/]')
    if response.error_count > 0 and str(response.first_error):
        c.print(f'     [dim]first error:[/] {rich_escape(str(response.first_error))}')
    c.print()


# Sub-app factory — same three commands for both `dashboard` and `data-view`,
# bound to the right Enum__Saved_Object__Type. Keeps the wire format symmetric.

def make_saved_objects_app(label: str, object_type: Enum__Saved_Object__Type, help_text: str) -> typer.Typer:
    sub_app = typer.Typer(help=help_text, no_args_is_help=True)

    @sub_app.command('list')
    @aws_error_handler
    def list_cmd(stack_name: Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists.'),
                 password  : Optional[str] = typer.Option  (None, '--password', help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                 page_size : int           = typer.Option  (100,  '--page-size', help='Max objects per Kibana _find page.')):
        f"""List {label}s on the stack."""
        saved_objects_list_cmd(label, object_type, stack_name, password, page_size)

    @sub_app.command('export')
    @aws_error_handler
    def export_cmd(stack_name             : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists.'),
                   output                  : str           = typer.Option  (..., '--output', '-o', help='Where to write the ndjson export.'),
                   password                : Optional[str] = typer.Option  (None, '--password', help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                   include_references_deep : bool          = typer.Option  (True, '--deep/--no-deep', help='Pull in referenced objects (lens/visualization/search/data-view) so the ndjson is self-contained.')):
        f"""Export all {label}s as ndjson."""
        saved_objects_export_cmd(label, object_type, stack_name, password, output, include_references_deep)

    @sub_app.command('import')
    @aws_error_handler
    def import_cmd(input_path : str           = typer.Argument(...,  help='Path to a Kibana ndjson export.'),
                   stack_name : Optional[str] = typer.Option  (None, '--stack', help='Stack name. Auto-picks when only one stack exists.'),
                   password   : Optional[str] = typer.Option  (None, '--password', help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                   overwrite  : bool          = typer.Option  (True, '--overwrite/--no-overwrite', help='Replace conflicting objects (Kibana default behaviour).')):
        f"""Import {label}s from an ndjson file."""
        saved_objects_import_cmd(label, stack_name, password, input_path, overwrite)

    return sub_app


dashboard_app = make_saved_objects_app(label       = 'dashboard'                                ,
                                        object_type = Enum__Saved_Object__Type.DASHBOARD          ,
                                        help_text   = 'Manage Kibana dashboards (list / export / import).')
data_view_app = make_saved_objects_app(label       = 'data view'                                ,
                                        object_type = Enum__Saved_Object__Type.DATA_VIEW          ,
                                        help_text   = 'Manage Kibana data views (renamed "index pattern" in 8.x).')

app.add_typer(dashboard_app, name='dashboard')
app.add_typer(data_view_app, name='data-view')
