# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama CLI
# Typer app: sp ollama create / list / info / delete / health / wait / models / pull
# Tier-2A pattern: thin wrapper — logic lives in Ollama__Service.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing import Optional

import typer
from rich.console import Console

from sg_compute_specs.ollama.cli.Renderers                           import (render_create ,
                                                                                  render_delete ,
                                                                                  render_info   ,
                                                                                  render_list   )
from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request import Schema__Ollama__Create__Request
from sg_compute_specs.ollama.service.Ollama__Service                 import Ollama__Service, DEFAULT_REGION

app = typer.Typer(no_args_is_help=True,
                  help='Manage ephemeral Ollama EC2 stacks',
                  add_completion=False)

DEBUG_TRACE = False


@app.callback()
def _root(debug: bool = typer.Option(False, '--debug',
                                     help='Show full Python traceback on errors.')):
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _svc() -> Ollama__Service:
    return Ollama__Service().setup()


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
            c = Console(highlight=False, stderr=True)
            c.print()
            c.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
            if not DEBUG_TRACE:
                c.print('     [dim]› Re-run with [bold]sp ollama --debug ...[/] to see the full traceback.[/]')
            if DEBUG_TRACE:
                c.print()
                c.print('[dim]── traceback ────────────────────────────────────[/]')
                c.print(traceback.format_exc(), end='')
            c.print()
            raise typer.Exit(2)
    return wrapped


def resolve_stack_name(svc: Ollama__Service, provided: Optional[str], region: str) -> str:
    if provided:
        return provided
    listing      = svc.list_stacks(region)
    names        = [s.stack_name for s in listing.stacks if s.stack_name]
    region_label = listing.region or 'the current region'
    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No Ollama stacks in {region_label}.[/]  Run: [bold]sp ollama create[/]\n')
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


@app.command()
@_err_handler
def create(
    name          : Optional[str] = typer.Argument(None, help='Stack name; auto-generated if omitted.'),
    region        : str           = typer.Option(DEFAULT_REGION    , '--region'       , '-r', help='AWS region.'                          ),
    instance_type : str           = typer.Option('g4dn.xlarge'     , '--instance-type', '-t', help='EC2 instance type.'                   ),
    from_ami      : Optional[str] = typer.Option(None              , '--ami'          ,       help='AMI ID; latest AL2023 used if omitted.'),
    caller_ip     : Optional[str] = typer.Option(None              , '--caller-ip'    ,       help='Source IP; auto-detected if omitted.' ),
    model         : str           = typer.Option('qwen2.5-coder:7b', '--model'        ,       help='Ollama model reference.'              ),
    allowed_cidr  : str           = typer.Option(''                , '--allowed-cidr' ,       help='CIDR for port 11434 (blank=caller/32).'),
    max_hours     : int           = typer.Option(4                 , '--max-hours'    ,       help='Auto-terminate after N hours; 0=off.' ),
    no_pull       : bool          = typer.Option(False             , '--no-pull'      ,       help='Skip ollama pull (baked AMI).'        ),
    cpu_only      : bool          = typer.Option(False             , '--cpu-only'     ,       help='Allow CPU-only instance types.'       ),
    wait          : bool          = typer.Option(False             , '--wait'         ,       help='Block until Ollama API is ready.'     ),
) -> None:
    c   = Console(highlight=False, width=200)
    svc = _svc()
    req = Schema__Ollama__Create__Request(
        region        = region             ,
        instance_type = instance_type      ,
        from_ami      = from_ami  or ''    ,
        stack_name    = name      or ''    ,
        caller_ip     = caller_ip or ''    ,
        model_name    = model              ,
        allowed_cidr  = allowed_cidr       ,
        max_hours     = max_hours          ,
        pull_on_boot  = not no_pull        ,
        gpu_required  = not cpu_only       ,
    )
    resp = svc.create_stack(req)
    render_create(resp, c)
    if wait:
        _wait_healthy(svc, resp.stack_info.instance_id, resp.stack_info.stack_name,
                      region, 600, c)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')) -> None:
    listing = _svc().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
) -> None:
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Ollama stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def delete(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
) -> None:
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    render_delete(name, resp.deleted, c)
    if not resp.deleted:
        raise typer.Exit(1)


@app.command()
@_err_handler
def wait(
    name        : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region      : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
    timeout_sec : int           = typer.Option(600, '--timeout', help='Max seconds to wait.'),
) -> None:
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Ollama stack matched {name!r}[/]')
        raise typer.Exit(1)
    _wait_healthy(svc, data.instance_id, name, region, timeout_sec, c)


@app.command()
@_err_handler
def health(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
    timeout: int           = typer.Option(600, '--timeout', help='Max wait seconds.'),
) -> None:
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Ollama stack matched {name!r}[/]')
        raise typer.Exit(1)
    _wait_healthy(svc, data.instance_id, name, region, timeout, c)


@app.command()
@_err_handler
def models(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
) -> None:
    import json, urllib.request
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Ollama stack matched {name!r}[/]')
        raise typer.Exit(1)
    try:
        with urllib.request.urlopen(
                f'http://{data.private_ip}:11434/api/tags', timeout=10) as r:
            raw = r.read().decode()
    except Exception:
        raw = None
    if raw:
        for m in json.loads(raw).get('models', []):
            c.print(f"  {m.get('name', '?')}")
    else:
        c.print('  [red]could not reach Ollama API[/]')
        raise typer.Exit(1)


@app.command()
@_err_handler
def pull(
    model_name  : str           = typer.Argument(..., help='Model to pull (e.g. llama3.3).'),
    name        : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region      : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
) -> None:
    from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Ollama stack matched {name!r}[/]')
        raise typer.Exit(1)
    c.print(f'  pulling [bold]{model_name}[/] on {name}…')
    out = EC2__Instance__Helper().run_command(region, data.instance_id,
                                              f'ollama pull {model_name}')
    c.print(out or '[green]done[/]')


def _wait_healthy(svc: Ollama__Service, instance_id: str, stack_name: str,
                  region: str, timeout_sec: int, c: Console) -> None:
    from sg_compute.platforms.ec2.health.Health__Poller      import Health__Poller
    from sg_compute.platforms.ec2.health.Health__HTTP__Probe import Health__HTTP__Probe
    from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper  import EC2__Instance__Helper
    c.print(f'  [dim]Waiting for [bold]{stack_name}[/] to become healthy (timeout {timeout_sec}s)…[/]')
    instance_helper = EC2__Instance__Helper()
    # Phase 1 — wait for EC2 running state
    running = instance_helper.wait_for_running(region, instance_id, timeout_sec=timeout_sec)
    if not running:
        c.print(f'  [red]timed out[/] waiting for instance to start')
        raise typer.Exit(1)
    # Phase 2 — re-fetch to get assigned private IP, then probe port 11434
    data = svc.get_stack_info(region, stack_name)
    if not data or not data.private_ip:
        c.print(f'  [red]instance running but no private IP found[/]')
        raise typer.Exit(1)
    poller = Health__Poller(instance=instance_helper, probe=Health__HTTP__Probe())
    ok = poller.wait_healthy(region=region, instance_id=instance_id,
                             public_ip=data.private_ip,
                             health_path='/api/tags',
                             port=11434,
                             timeout_sec=timeout_sec)
    if ok:
        c.print(f'  [green]healthy[/] — {data.api_base_url or stack_name}')
    else:
        c.print(f'  [red]timed out[/] after {timeout_sec}s')
        raise typer.Exit(1)
