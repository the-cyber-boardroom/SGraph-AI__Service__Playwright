# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — sp neko
# Typer CLI for managing ephemeral Neko (n.eko WebRTC browser) EC2 stacks.
# All logic lives in Neko__Service — this file only constructs the service,
# calls one method, and renders via Renderers. Tier-2A pattern.
#
# Commands:
#   sp neko create [name]   — provision a Neko stack
#   sp neko list            — list all Neko stacks in region
#   sp neko info [name]     — show stack details (get public IP here)
#   sp neko delete [name]   — terminate a stack
#   sp neko connect [name]  — open an SSM shell on the instance
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.neko.cli.Renderers                           import (render_create,
                                                                                             render_info  ,
                                                                                             render_list  )
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Create__Request import Schema__Neko__Stack__Create__Request
from sgraph_ai_service_playwright__cli.neko.service.Neko__Service                   import DEFAULT_INSTANCE_TYPE, DEFAULT_REGION, Neko__Service


DEBUG_TRACE = False

app = typer.Typer(no_args_is_help=True,
                  help='Manage ephemeral Neko (WebRTC browser) EC2 stacks.')


@app.callback()
def _neko_root(debug: bool = typer.Option(False, '--debug',
                                           help='Show full Python traceback on errors.')):
    """Manage ephemeral Neko WebRTC browser stacks. Pass --debug for full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _service() -> Neko__Service:
    return Neko__Service().setup()


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
                console.print('     [dim]› Re-run with [bold]sp neko --debug ...[/] for the full traceback.[/]')
            else:
                console.print()
                console.print('[dim]── traceback ────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(2)
    return wrapped


def _resolve_stack_name(service: Neko__Service, provided: Optional[str], region: str) -> str:
    """Auto-select when one stack exists, prompt when many, error when none."""
    if provided:
        return provided
    listing      = service.list_stacks(region)
    names        = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or region

    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No Neko stacks in {region_label}.[/]  Run: [bold]sp neko create[/]\n')
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


# ── commands ──────────────────────────────────────────────────────────────────

@app.command()
@_err_handler
def create(name           : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as neko-{adjective}-{scientist} if omitted.'),
           region         : str           = typer.Option(DEFAULT_REGION       , '--region'       , '-r', help='AWS region.'),
           instance_type  : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type', '-t', help='EC2 instance type.'),
           admin_password : Optional[str] = typer.Option(None, '--admin-password' , help='Neko admin password (full keyboard/mouse control). Auto-generated if omitted.'),
           member_password: Optional[str] = typer.Option(None, '--member-password', help='Neko member password (view-only). Auto-generated if omitted.')):
    """Provision a Neko (WebRTC browser) EC2 stack."""
    c       = Console(highlight=False, width=200)
    request = Schema__Neko__Stack__Create__Request(
        stack_name      = name            or '',
        region          = region               ,
        instance_type   = instance_type        ,
        admin_password  = admin_password  or '',
        member_password = member_password or '')
    resp = _service().create_stack(request)
    render_create(resp, c)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """List all Neko stacks in the region."""
    render_list(_service().list_stacks(region), Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Show details for a single Neko stack (includes public IP once running)."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Fetching {name!r} from {region}…[/]')
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Neko stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def delete(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Terminate a Neko stack. All state on the EC2 is wiped."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    if not resp.deleted:
        c.print(f'  [red]✗  No Neko stack matched {name!r} or terminate failed[/]')
        raise typer.Exit(1)
    c.print(f'  ✅  Terminated [dim]{resp.target}[/] ({name})')


@app.command()
@_err_handler
def connect(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
            region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Open an SSM shell session on the Neko stack instance."""
    import os
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Resolving {name!r}…[/]')
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Neko stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(data.instance_id)
    c.print(f'  [dim]Connecting to {name} ({iid}) in {region}…[/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session', '--target', iid, '--region', region])
