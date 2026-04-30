# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — sp firefox
# Typer CLI for managing ephemeral Firefox (jlesage/firefox noVNC) EC2 stacks
# with mitmproxy for traffic inspection.
# All logic lives in Firefox__Service — this file only constructs the service,
# calls one method, and renders via Renderers. Tier-2A pattern.
#
# Commands:
#   sp firefox create [name]      — provision a Firefox + mitmproxy stack
#   sp firefox list               — list all Firefox stacks in region
#   sp firefox info [name]        — show stack details (viewer + mitmweb URLs)
#   sp firefox wait [name]        — block until instance is running
#   sp firefox health [name]      — instant EC2 state probe
#   sp firefox delete [name]      — terminate a stack
#   sp firefox connect [name]     — open an SSM shell on the instance
#   sp firefox set-interceptor    — push a new interceptor to a live stack (hot-reload)
#   sp firefox interceptors       — list baked mitmproxy interceptor examples
#   sp firefox create-from-ami    — fast-boot a new stack from an existing AMI
#   sp firefox ami create [name]  — bake an AMI from a running stack
#   sp firefox ami list           — list available Firefox AMIs
#   sp firefox ami wait AMI_ID    — wait until a bake is complete
#   sp firefox ami delete AMI_ID  — deregister AMI + snapshots
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.firefox.cli.Renderers                        import (render_ami_create       ,
                                                                                             render_ami_list         ,
                                                                                             render_create           ,
                                                                                             render_health           ,
                                                                                             render_info             ,
                                                                                             render_interceptors     ,
                                                                                             render_list             ,
                                                                                             render_set_interceptor  )
from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Interceptor__Kind       import Enum__Firefox__Interceptor__Kind
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Interceptor__Choice import Schema__Firefox__Interceptor__Choice
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Interceptor__Resolver import list_examples
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service             import DEFAULT_INSTANCE_TYPE, DEFAULT_REGION, Firefox__Service


DEBUG_TRACE = False

app = typer.Typer(no_args_is_help=True,
                  help='Manage ephemeral Firefox (noVNC browser) EC2 stacks with mitmproxy traffic inspection.')


@app.callback()
def _firefox_root(debug: bool = typer.Option(False, '--debug',
                                              help='Show full Python traceback on errors.')):
    """Manage ephemeral Firefox noVNC browser stacks. Pass --debug for full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _service() -> Firefox__Service:
    return Firefox__Service().setup()


def _err_handler(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            console = Console(highlight=False, stderr=True)
            console.print()
            console.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
            if not DEBUG_TRACE:
                console.print('     [dim]› Re-run with [bold]sp firefox --debug ...[/] for the full traceback.[/]')
            else:
                console.print()
                console.print('[dim]── traceback ────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(2)
    return wrapped


def _check_script_source(script_path: str, source: str) -> None:
    """Emit a clear diagnostic and exit if source contains control characters that break heredocs."""
    bad = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        for col, ch in enumerate(line, start=1):
            code = ord(ch)
            if (0x00 <= code <= 0x08) or (0x0b <= code <= 0x1f) or code == 0x7f:  # null + control chars except tab/newline
                bad.append((lineno, col, repr(ch)))
    if not bad:
        return
    c = Console(highlight=False, stderr=True)
    c.print()
    c.print(f'  [red]✗  {script_path} contains control characters that break bash heredocs[/]')
    c.print()
    for lineno, col, r in bad[:10]:
        c.print(f'    line {lineno:>4}, col {col:>3}: {r}')
    if len(bad) > 10:
        c.print(f'    … and {len(bad) - 10} more')
    c.print()
    raise typer.Exit(2)


def _read_env_file(path: Optional[str]) -> str:
    if not path:
        return ''
    with open(path, 'r', encoding='utf-8') as fh:
        content = fh.read()
    _check_script_source(path, content)
    return content


def _interceptor_choice(name: Optional[str], script_path: Optional[str]) -> Schema__Firefox__Interceptor__Choice:
    if name and script_path:
        raise typer.BadParameter('Pass at most one of --interceptor / --interceptor-script.')
    if name:
        return Schema__Firefox__Interceptor__Choice(kind=Enum__Firefox__Interceptor__Kind.NAME, name=name)
    if script_path:
        with open(script_path, 'r', encoding='utf-8') as fh:
            source = fh.read()
        _check_script_source(script_path, source)
        return Schema__Firefox__Interceptor__Choice(kind=Enum__Firefox__Interceptor__Kind.INLINE, inline_source=source)
    return Schema__Firefox__Interceptor__Choice()                                   # NONE


def _resolve_stack_name(service: Firefox__Service, provided: Optional[str], region: str) -> str:
    """Auto-select when one stack exists, prompt when many, error when none."""
    if provided:
        return provided
    listing      = service.list_stacks(region)
    names        = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or region

    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No Firefox stacks in {region_label}.[/]  Run: [bold]sp firefox create[/]\n')
        raise typer.Exit(1)

    if len(names) == 1:
        Console(highlight=False).print(f'\n  [dim]One stack found — using [bold]{names[0]}[/][/]')
        return names[0]

    c = Console(highlight=False)
    c.print(f'\n  [bold]Multiple stacks in {region_label}:[/]')
    for idx, name in enumerate(names, start=1):
        c.print(f'    {idx}. {name}')
    raw = typer.prompt('\n  Pick a stack number', type=int)
    try:
        choice = int(raw)
    except (TypeError, ValueError):
        choice = -1
    if choice < 1 or choice > len(names):
        Console(highlight=False, stderr=True).print(f'\n  [red]Invalid selection: {raw}[/]\n')
        raise typer.Exit(1)
    return names[choice - 1]


# ── ami sub-app ───────────────────────────────────────────────────────────────

ami_app = typer.Typer(help='Manage Firefox AMIs (bake / list / wait / delete).', no_args_is_help=True)


@ami_app.command('create')
@_err_handler
def ami_create(name      : Optional[str] = typer.Argument(None, help='Stack to bake from; auto-selected when only one exists.'),
               region    : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
               ami_name  : Optional[str] = typer.Option(None , '--name', help='AMI name; auto-generated if omitted.'),
               wait      : bool          = typer.Option(False, '--wait', help='Block until AMI is available (~5-10 min).')):
    """Bake an AMI from a running Firefox stack."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Submitting AMI bake for {name!r}…[/]')
    resp = svc.create_ami(region, name, ami_name or '')
    render_ami_create(resp, c)
    if wait:
        ami_id = str(resp.ami_id)
        c.print(f'  [dim]Waiting for {ami_id} to become available…[/]')
        from rich.status import Status
        status = Status('', console=c, spinner='dots')
        status.start()
        def _tick(t):
            status.update(f'  [dim][{t["elapsed_ms"]//1000:>3}s  #{t["attempt"]:02d}]  state=[bold]{t["state"]}[/][/]')
        try:
            final = svc.wait_for_ami(region, ami_id, on_progress=_tick)
        finally:
            status.stop()
        colour = 'green' if final == 'available' else 'red'
        c.print(f'  [{colour}]{ami_id}  →  {final}[/]')
        c.print()
        if final != 'available':
            raise typer.Exit(1)


@ami_app.command('list')
@_err_handler
def ami_list(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List Firefox AMIs in the region."""
    render_ami_list(_service().list_amis(region), Console(highlight=False, width=200))


@ami_app.command('wait')
@_err_handler
def ami_wait(ami_id     : str = typer.Argument(..., help='AMI ID to wait for.'),
             region     : str = typer.Option(DEFAULT_REGION, '--region', '-r'),
             timeout_sec: int = typer.Option(1200, '--timeout'),
             poll_sec   : int = typer.Option(15  , '--poll'  )):
    """Wait until a Firefox AMI bake is complete."""
    c   = Console(highlight=False, width=200)
    svc = _service()
    c.print(f'  [dim]Waiting for {ami_id}…[/]')
    from rich.status import Status
    status = Status('', console=c, spinner='dots')
    status.start()
    def _tick(t):
        status.update(f'  [dim][{t["elapsed_ms"]//1000:>3}s  #{t["attempt"]:02d}]  state=[bold]{t["state"]}[/][/]')
    try:
        final = svc.wait_for_ami(region, ami_id, timeout_sec=timeout_sec, poll_sec=poll_sec, on_progress=_tick)
    finally:
        status.stop()
    colour = 'green' if final == 'available' else 'red'
    c.print(f'  [{colour}]{ami_id}  →  {final}[/]\n')
    if final != 'available':
        raise typer.Exit(1)


@ami_app.command('delete')
@_err_handler
def ami_delete(ami_id : str  = typer.Argument(..., help='AMI ID to delete.'),
               region : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
               yes    : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.')):
    """Deregister a Firefox AMI and delete its snapshots."""
    c = Console(highlight=False, width=200)
    if not yes:
        typer.confirm(f'  Deregister {ami_id} and delete snapshots?', abort=True)
    result = _service().delete_ami(region, ami_id)
    if result.get('deleted'):
        c.print(f'  ✅  {ami_id} deregistered  [dim]({result.get("snapshots", 0)} snapshot(s) deleted)[/]')
    else:
        c.print(f'  [red]✗  deregister failed for {ami_id}[/]')
        raise typer.Exit(1)


# ── commands ──────────────────────────────────────────────────────────────────

@app.command()
@_err_handler
def create(name              : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as firefox-{adjective}-{scientist} if omitted.'),
           region            : str           = typer.Option(DEFAULT_REGION       , '--region'           , '-r', help='AWS region.'),
           instance_type     : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type'    , '-t', help='EC2 instance type.'),
           from_ami          : Optional[str] = typer.Option(None                 , '--ami'              ,       help='AMI ID; latest AL2023 used if omitted.'),
           caller_ip         : Optional[str] = typer.Option(None                 , '--caller-ip'        ,       help='Source IP for SG rule; auto-detected if omitted.'),
           password          : Optional[str] = typer.Option(None                 , '--password'         ,       help='Web UI password. Auto-generated if omitted.'),
           interceptor       : Optional[str] = typer.Option(None                 , '--interceptor'      ,       help='Name of a baked mitmproxy interceptor (see `sp firefox interceptors`).'),
           interceptor_script: Optional[str] = typer.Option(None                 , '--interceptor-script',      help='Path to a local Python file; embedded inline at create time.'),
           env_file          : Optional[str] = typer.Option(None                 , '--env-file'         ,       help='Path to a .env file; vars injected into mitmproxy at boot (tmpfs, never baked into AMI).'),
           wait              : bool          = typer.Option(False                , '--wait'             ,       help='Block until instance is running.')):
    """Provision a Firefox (noVNC browser) + mitmproxy EC2 stack."""
    c       = Console(highlight=False, width=200)
    choice  = _interceptor_choice(interceptor, interceptor_script)
    request = Schema__Firefox__Stack__Create__Request(
        stack_name    = name          or '',
        region        = region             ,
        instance_type = instance_type      ,
        from_ami      = from_ami      or '',
        caller_ip     = caller_ip     or '',
        password      = password      or '',
        interceptor   = choice             ,
        env_source    = _read_env_file(env_file))
    svc  = _service()
    resp = svc.create_stack(request)
    render_create(resp, c)
    if wait:
        stack_name = str(resp.stack_name)
        c.print(f'  [dim]Waiting for {stack_name!r} to become running…[/]')
        h = svc.health(region, stack_name, timeout_sec=300, poll_sec=10)
        render_health(h, c)
        if not h.healthy:
            raise typer.Exit(1)
        data = svc.get_stack_info(region, stack_name)
        if data:
            render_info(data, c)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """List all Firefox stacks in the region."""
    render_list(_service().list_stacks(region), Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Show details for a single Firefox stack (includes viewer and mitmweb URLs once running)."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Firefox stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def wait(name       : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region     : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout_sec: int           = typer.Option(300            , '--timeout', help='Max seconds to wait.'),
         poll_sec   : int           = typer.Option(10             , '--poll'   , help='Seconds between polls.')):
    """Wait until the Firefox instance is running."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Waiting for {name!r} to become running (timeout={timeout_sec}s)…[/]')
    h = svc.health(region, name, timeout_sec=timeout_sec, poll_sec=poll_sec)
    render_health(h, c)
    if not h.healthy:
        raise typer.Exit(1)


@app.command()
@_err_handler
def health(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Quick EC2 state probe (no waiting)."""
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    h    = svc.health(region, name, timeout_sec=0, poll_sec=1)
    render_health(h, Console(highlight=False, width=200))


@app.command()
@_err_handler
def delete(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Terminate a Firefox stack."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    if not resp.deleted:
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  ✅  {resp.message}  [dim]({resp.elapsed_ms / 1000:.1f}s)[/]')


@app.command()
@_err_handler
def connect(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
            region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Open an SSM shell session on the Firefox stack instance."""
    import os
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Firefox stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(data.instance_id)
    c.print(f'  [dim]Connecting to {name} ({iid}) in {region}…[/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session', '--target', iid, '--region', region])


@app.command(name='set-interceptor')
@_err_handler
def set_interceptor(name              : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
                    region            : str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
                    interceptor       : Optional[str] = typer.Option(None, '--interceptor'      , help='Name of a baked example (see `sp firefox interceptors`).'),
                    interceptor_script: Optional[str] = typer.Option(None, '--interceptor-script', help='Path to a local Python file; pushed live via SSM.')):
    """Push a new mitmproxy interceptor script to a running stack (hot-reload, no restart)."""
    c      = Console(highlight=False, width=200)
    svc    = _service()
    name   = _resolve_stack_name(svc, name, region)
    choice = _interceptor_choice(interceptor, interceptor_script)
    c.print(f'  [dim]Pushing interceptor to {name!r} via SSM…[/]')
    resp   = svc.set_interceptor(region, name, choice)
    render_set_interceptor(resp, c)
    if not resp.success:
        raise typer.Exit(1)


@app.command(name='create-from-ami')
@_err_handler
def create_from_ami(ami_id            : Optional[str] = typer.Argument(None, help='AMI ID; latest Firefox AMI used if omitted.'),
                    name              : Optional[str] = typer.Option(None                 , '--name'             , help='Stack name; auto-generated if omitted.'),
                    region            : str           = typer.Option(DEFAULT_REGION       , '--region'   , '-r'  ),
                    instance_type     : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type', '-t'),
                    caller_ip         : Optional[str] = typer.Option(None                 , '--caller-ip'        ),
                    password          : Optional[str] = typer.Option(None                 , '--password'         , help='Web UI password. Auto-generated if omitted.'),
                    interceptor       : Optional[str] = typer.Option(None                 , '--interceptor'      ),
                    interceptor_script: Optional[str] = typer.Option(None                 , '--interceptor-script'),
                    env_file          : Optional[str] = typer.Option(None                 , '--env-file'         , help='Path to a .env file; vars injected into mitmproxy at boot (tmpfs, never baked into AMI).'),
                    wait              : bool          = typer.Option(False                , '--wait'             )):
    """Launch a new Firefox stack from an existing AMI (fast boot — skips full install)."""
    c      = Console(highlight=False, width=200)
    svc    = _service()
    choice = _interceptor_choice(interceptor, interceptor_script)

    if not ami_id:
        amis = svc.list_amis(region)
        avail = [a for a in amis if str(a.state) == 'available']
        if not avail:
            c.print(f'  [red]✗  No available Firefox AMIs in {region}.[/]  Run: [bold]sp firefox ami create[/]')
            raise typer.Exit(1)
        ami_id = str(sorted(avail, key=lambda a: str(a.creation_date), reverse=True)[0].ami_id)
        c.print(f'  [dim]Using latest AMI: [bold]{ami_id}[/][/]')

    request = Schema__Firefox__Stack__Create__Request(
        stack_name    = name          or '',
        region        = region             ,
        instance_type = instance_type      ,
        from_ami      = ami_id             ,
        caller_ip     = caller_ip     or '',
        password      = password      or '',
        interceptor   = choice             ,
        env_source    = _read_env_file(env_file))
    resp = svc.create_from_ami(request)
    render_create(resp, c)
    if wait:
        stack_name = str(resp.stack_name)
        c.print(f'  [dim]Waiting for {stack_name!r} to become running…[/]')
        h = svc.health(region, stack_name, timeout_sec=300, poll_sec=10)
        render_health(h, c)
        if not h.healthy:
            raise typer.Exit(1)
        data = svc.get_stack_info(region, stack_name)
        if data:
            render_info(data, c)


@app.command()
@_err_handler
def interceptors():
    """List baked mitmproxy interceptor examples (pass name to --interceptor on create)."""
    render_interceptors(list_examples(), Console(highlight=False, width=200))


app.add_typer(ami_app, name='ami')
