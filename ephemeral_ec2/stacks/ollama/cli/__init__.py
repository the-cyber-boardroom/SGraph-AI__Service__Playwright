# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama CLI
# Typer app: ec2 ollama create / list / info / delete / health / models / pull
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console

from ephemeral_ec2.stacks.ollama.cli.Renderers                           import (render_create ,
                                                                                  render_delete ,
                                                                                  render_info   ,
                                                                                  render_list   )
from ephemeral_ec2.stacks.ollama.schemas.Schema__Ollama__Create__Request import Schema__Ollama__Create__Request
from ephemeral_ec2.stacks.ollama.service.Ollama__Service                 import Ollama__Service

app = typer.Typer(help='Manage ephemeral Ollama EC2 stacks', add_completion=False)
_c  = Console()


def _svc() -> Ollama__Service:
    return Ollama__Service().setup()


@app.command('create')
def create(
    region        : str  = typer.Option('eu-west-2'        , help='AWS region'                          ),
    instance_type : str  = typer.Option('g4dn.xlarge'      , help='EC2 instance type'                   ),
    from_ami      : str  = typer.Option(''                 , help='AMI ID (blank = latest AL2023)'       ),
    name          : str  = typer.Option(''                 , help='Stack name (blank = auto)'            ),
    model         : str  = typer.Option('qwen2.5-coder:7b' , help='Ollama model reference'               ),
    allowed_cidr  : str  = typer.Option(''                 , help='CIDR for port 11434 (blank = caller)' ),
    max_hours     : int  = typer.Option(4                  , help='Auto-terminate after N hours (0=off)' ),
    no_pull       : bool = typer.Option(False              , help='Skip ollama pull (baked AMI)'         ),
    cpu_only      : bool = typer.Option(False              , help='Allow CPU-only instance types'        ),
) -> None:
    req = Schema__Ollama__Create__Request(
        region        = region               ,
        instance_type = instance_type        ,
        from_ami      = from_ami             ,
        stack_name    = name                 ,
        model_name    = model                ,
        allowed_cidr  = allowed_cidr         ,
        max_hours     = max_hours            ,
        pull_on_boot  = not no_pull          ,
        gpu_required  = not cpu_only         ,
    )
    resp = _svc().create_stack(req)
    render_create(resp, _c)


@app.command('list')
def list_stacks(
    region : str = typer.Option('eu-west-2', help='AWS region'),
) -> None:
    listing = _svc().list_stacks(region)
    render_list(listing, _c)


@app.command('info')
def info(
    stack_name : str = typer.Argument(..., help='Stack name'),
    region     : str = typer.Option('eu-west-2', help='AWS region'),
) -> None:
    result = _svc().get_stack_info(region, stack_name)
    if result is None:
        _c.print(f'  [red]stack not found:[/] {stack_name}')
        raise typer.Exit(1)
    render_info(result, _c)


@app.command('delete')
def delete(
    stack_name : str = typer.Argument(..., help='Stack name'),
    region     : str = typer.Option('eu-west-2', help='AWS region'),
) -> None:
    resp = _svc().delete_stack(region, stack_name)
    render_delete(stack_name, resp.deleted, _c)


@app.command('health')
def health(
    stack_name : str = typer.Argument(..., help='Stack name'),
    region     : str = typer.Option('eu-west-2', help='AWS region'),
    timeout    : int = typer.Option(600, help='Max wait seconds'),
) -> None:
    from ephemeral_ec2.helpers.health.Health__HTTP__Probe import Health__HTTP__Probe
    from ephemeral_ec2.helpers.health.Health__Poller      import Health__Poller
    from ephemeral_ec2.helpers.aws.EC2__Instance__Helper  import EC2__Instance__Helper

    svc         = _svc()
    info_result = svc.get_stack_info(region, stack_name)
    if info_result is None:
        _c.print(f'  [red]stack not found:[/] {stack_name}')
        raise typer.Exit(1)

    _c.print(f'  polling health for [bold]{stack_name}[/] (timeout {timeout}s)…')
    poller = Health__Poller(instance=EC2__Instance__Helper(), probe=Health__HTTP__Probe())
    ok = poller.wait_healthy(
        region      = region                  ,
        instance_id = info_result.instance_id ,
        public_ip   = info_result.private_ip  ,  # Ollama: internal access only
        health_path = '/api/tags'             ,
        port        = 11434                   ,
        timeout_sec = timeout                 ,
    )
    if ok:
        _c.print(f'  [green]healthy[/] — {info_result.api_base_url or stack_name}')
    else:
        _c.print(f'  [red]timed out[/] after {timeout}s')
        raise typer.Exit(1)


@app.command('models')
def models(
    stack_name : str = typer.Argument(..., help='Stack name'),
    region     : str = typer.Option('eu-west-2', help='AWS region'),
) -> None:
    import json
    svc         = _svc()
    info_result = svc.get_stack_info(region, stack_name)
    if info_result is None:
        _c.print(f'  [red]stack not found:[/] {stack_name}')
        raise typer.Exit(1)
    import urllib.request
    try:
        with urllib.request.urlopen(
                f'http://{info_result.private_ip}:11434/api/tags', timeout=10) as r:
            raw = r.read().decode()
    except Exception:
        raw = None
    if raw:
        data = json.loads(raw)
        for m in data.get('models', []):
            _c.print(f"  {m.get('name', '?')}")
    else:
        _c.print('  [red]could not reach Ollama API[/]')
        raise typer.Exit(1)


@app.command('pull')
def pull(
    stack_name : str = typer.Argument(..., help='Stack name'),
    model_name : str = typer.Argument(..., help='Model to pull (e.g. llama3.3)'),
    region     : str = typer.Option('eu-west-2', help='AWS region'),
) -> None:
    from ephemeral_ec2.helpers.aws.EC2__Instance__Helper import EC2__Instance__Helper
    svc         = _svc()
    info_result = svc.get_stack_info(region, stack_name)
    if info_result is None:
        _c.print(f'  [red]stack not found:[/] {stack_name}')
        raise typer.Exit(1)
    _c.print(f'  pulling [bold]{model_name}[/] on {stack_name}…')
    out = EC2__Instance__Helper().run_command(region, info_result.instance_id,
                                              f'ollama pull {model_name}')
    _c.print(out or '[green]done[/]')
