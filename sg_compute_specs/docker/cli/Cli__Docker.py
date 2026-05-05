# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Cli__Docker
# Per-spec CLI app. Mounted at: sg-compute spec docker <verb>
#
# Commands
# ────────
#   sg-compute spec docker list   [--region X]
#   sg-compute spec docker info   <stack-name> [--region X]
#   sg-compute spec docker create [--region X] [--instance-type T] [--max-hours N]
#                                  [--name X] [--registry R] [--api-key K]
#   sg-compute spec docker delete <stack-name> [--region X] [--yes]
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console                                                                    import Console

from sg_compute_specs.docker.cli.Renderers                                          import (render_create ,
                                                                                             render_delete ,
                                                                                             render_info   ,
                                                                                             render_list   )

DEFAULT_REGION = 'eu-west-2'

app = typer.Typer(no_args_is_help=True,
                  help='Manage docker compute nodes — ephemeral EC2 instances with Docker CE.')


def _service():
    from sg_compute_specs.docker.service.Docker__Service import Docker__Service
    return Docker__Service().setup()


@app.command()
def list(region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):

    try:
        listing = _service().list_stacks(region=region)
        render_list(listing, Console(highlight=False, width=200))
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def info(stack_name: str = typer.Argument(..., help='Docker stack name.'),
         region    : str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):

    try:
        result = _service().get_stack(stack_name=stack_name, region=region)
        if result is None:
            typer.echo(f'Stack {stack_name!r} not found in {region}', err=True)
            raise typer.Exit(1)
        render_info(result, Console(highlight=False, width=200))
    except typer.Exit:
        raise
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def create(region       : str = typer.Option(DEFAULT_REGION, '--region'       , '-r'),
           instance_type: str = typer.Option('t3.medium'  , '--instance-type' , '-t'),
           max_hours    : int = typer.Option(1            , '--max-hours'           ),
           name         : str = typer.Option(''           , '--name'               , help='Override stack name.'),
           registry     : str = typer.Option(''           , '--registry'            , help='ECR registry host (enables sidecar).'),
           api_key      : str = typer.Option(''           , '--api-key'             , help='SSM parameter path for the sidecar API key (e.g. /sg-compute/nodes/{node_id}/sidecar-api-key).')):

    from sg_compute_specs.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
    try:
        svc   = _service()
        sname = name or svc.name_gen.generate()
        req   = Schema__Docker__Create__Request(instance_type = instance_type ,
                                                max_hours     = max_hours     ,
                                                registry      = registry      ,
                                                api_key_ssm_path = api_key       )
        req.stack_name.__init__(sname)
        req.region.__init__(region)
        resp  = svc.create_stack(req)
        render_create(resp, Console(highlight=False, width=200))
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def delete(stack_name: str  = typer.Argument(..., help='Docker stack name.'),
           region    : str  = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           yes       : bool = typer.Option(False,           '--yes',    '-y', help='Skip confirmation.')):

    if not yes:
        typer.confirm(f'Delete docker stack {stack_name!r} in {region}?', abort=True)
    try:
        result = _service().delete_stack(stack_name=stack_name, region=region)
        render_delete(stack_name, result.deleted, Console(highlight=False, width=200))
        if not result.deleted:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise
