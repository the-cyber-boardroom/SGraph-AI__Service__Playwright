# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open Design CLI
# Typer app: ec2 open-design create / list / info / delete / health
# ═══════════════════════════════════════════════════════════════════════════════

import os
import webbrowser
from typing import Optional

import typer
from rich.console import Console

from ephemeral_ec2.stacks.open_design.cli.Renderers                                 import (render_create ,
                                                                                              render_delete ,
                                                                                              render_info   ,
                                                                                              render_list   )
from ephemeral_ec2.stacks.open_design.schemas.Schema__Open_Design__Create__Request  import Schema__Open_Design__Create__Request
from ephemeral_ec2.stacks.open_design.service.Open_Design__Service                  import Open_Design__Service

app = typer.Typer(help='Manage ephemeral Open Design EC2 stacks', add_completion=False)
_c  = Console()


def _svc() -> Open_Design__Service:
    return Open_Design__Service().setup()


@app.command('create')
def create(
    region        : str            = typer.Option('eu-west-2'  , help='AWS region'                         ),
    instance_type : str            = typer.Option('t3.large'   , help='EC2 instance type'                  ),
    from_ami      : str            = typer.Option(''           , help='AMI ID (blank = latest AL2023)'      ),
    name          : str            = typer.Option(''           , help='Stack name (blank = auto)'           ),
    api_key       : str            = typer.Option(''           , envvar='ANTHROPIC_API_KEY',
                                                                 help='Anthropic API key'                   ),
    ollama_ip     : str            = typer.Option(''           , help='Ollama EC2 private IP'               ),
    ref           : str            = typer.Option('main'       , help='open-design git ref'                 ),
    max_hours     : int            = typer.Option(1            , help='Auto-terminate after N hours (0=off)'),
    fast_boot     : bool           = typer.Option(False        , help='Skip pnpm build (baked AMI)'         ),
    open_browser  : bool           = typer.Option(False, '--open', help='Open viewer URL in browser'        ),
) -> None:
    ollama_url = f'http://{ollama_ip}:11434/v1' if ollama_ip else ''
    req = Schema__Open_Design__Create__Request(
        region          = region        ,
        instance_type   = instance_type ,
        from_ami        = from_ami      ,
        stack_name      = name          ,
        api_key         = api_key       ,
        ollama_base_url = ollama_url    ,
        open_design_ref = ref           ,
        max_hours       = max_hours     ,
        fast_boot       = fast_boot     ,
    )
    resp = _svc().create_stack(req)
    render_create(resp, _c)
    if open_browser and resp.stack_info.viewer_url:
        webbrowser.open(resp.stack_info.viewer_url)


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
    stack_name  : str = typer.Argument(..., help='Stack name'),
    region      : str = typer.Option('eu-west-2', help='AWS region'),
    timeout     : int = typer.Option(600, help='Max wait seconds'),
) -> None:
    from ephemeral_ec2.helpers.health.Health__Poller    import Health__Poller
    from ephemeral_ec2.helpers.health.Health__HTTP__Probe import Health__HTTP__Probe
    from ephemeral_ec2.helpers.aws.EC2__Instance__Helper import EC2__Instance__Helper

    svc  = _svc()
    info_result = svc.get_stack_info(region, stack_name)
    if info_result is None:
        _c.print(f'  [red]stack not found:[/] {stack_name}')
        raise typer.Exit(1)

    _c.print(f'  polling health for [bold]{stack_name}[/] (timeout {timeout}s)…')
    poller = Health__Poller(instance=EC2__Instance__Helper(), probe=Health__HTTP__Probe())
    ok = poller.wait_healthy(
        region      = region                ,
        instance_id = info_result.instance_id,
        public_ip   = info_result.public_ip  ,
        timeout_sec = timeout               ,
    )
    if ok:
        _c.print(f'  [green]healthy[/] — {info_result.viewer_url or stack_name}')
    else:
        _c.print(f'  [red]timed out[/] after {timeout}s')
        raise typer.Exit(1)
