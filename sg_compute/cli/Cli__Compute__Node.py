# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cli__Compute__Node
# CLI subgroup: sg-compute node
#
# Commands
# ────────
#   sg-compute node list   [--region X]
#   sg-compute node info   <node-id> [--region X]
#   sg-compute node create <spec-id> [--region X] [--instance-type T] ...
#   sg-compute node delete <node-id> [--region X] [--yes]
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                    import Optional

import typer
from rich.console                                                              import Console

from sg_compute.cli.Renderers                                                 import render_node_list, render_node_info


DEFAULT_REGION = 'eu-west-2'

app = typer.Typer(no_args_is_help=True,
                  help='Manage compute nodes — ephemeral EC2 instances running a single spec.')


def _platform():
    from sg_compute.platforms.ec2.EC2__Platform import EC2__Platform
    return EC2__Platform().setup()


@app.command()
def list(region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """List all active compute nodes."""
    try:
        listing = _platform().list_nodes(region)
        render_node_list(listing, Console(highlight=False, width=200))
    except Exception as e:
        if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
            typer.echo(f'AWS credentials not configured: {e}', err=True)
            raise typer.Exit(1)
        raise


@app.command()
def info(node_id: str = typer.Argument(..., help='Node identifier (stack name).'),
         region : str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Show details for one compute node."""
    node = _platform().get_node(node_id, region)
    if node is None:
        typer.echo(f'Node {node_id!r} not found in {region}', err=True)
        raise typer.Exit(1)
    render_node_info(node, Console(highlight=False, width=200))


@app.command()
def delete(node_id: str = typer.Argument(..., help='Node identifier (stack name).'),
           region : str  = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           yes    : bool = typer.Option(False,           '--yes',    '-y', help='Skip confirmation.')):
    """Terminate a compute node."""
    if not yes:
        typer.confirm(f'Delete node {node_id!r} in {region}?', abort=True)
    result = _platform().delete_node(node_id, region)
    if result.deleted:
        typer.echo(f'Deleted: {node_id}')
    else:
        typer.echo(f'Failed:  {node_id} — {result.message}', err=True)
        raise typer.Exit(1)


@app.command()
def create(spec_id      : str = typer.Argument(..., help='Spec identifier (docker, podman, …)'),
           region       : str = typer.Option(DEFAULT_REGION, '--region',        '-r'),
           instance_type: str = typer.Option('t3.medium',   '--instance-type',  '-t'),
           max_hours    : int = typer.Option(1,              '--max-hours'            ),
           registry     : str = typer.Option('',             '--registry',            help='ECR registry host (enables host control plane sidecar).'),
           api_key      : str = typer.Option('',             '--api-key',             help='Host control plane API key (auto-generated if empty).'),
           name         : str = typer.Option('',             '--name',                help='Override stack name (auto-generated if empty).')):
    """Create a new compute node running the given spec."""
    if spec_id == 'docker':
        _create_docker(region, instance_type, max_hours, registry, api_key, name)
    elif spec_id == 'podman':
        _create_podman(region, instance_type, max_hours, name)
    else:
        typer.echo(f'create --spec {spec_id!r} not yet wired; supported: docker, podman', err=True)
        raise typer.Exit(1)


def _create_docker(region, instance_type, max_hours, registry, api_key, name):
    from sg_compute_specs.docker.schemas.Schema__Docker__Create__Request    import Schema__Docker__Create__Request
    from sg_compute_specs.docker.service.Docker__Service                    import Docker__Service
    svc  = Docker__Service().setup()
    sname = name or svc.name_gen.generate()
    req  = Schema__Docker__Create__Request(instance_type = instance_type ,
                                           max_hours     = max_hours     ,
                                           registry      = registry      ,
                                           api_key_value = api_key       )
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp = svc.create_stack(req)
    info = resp.stack_info
    typer.echo(f'Created : {info.stack_name}')
    typer.echo(f'Instance: {info.instance_id}  ({info.instance_type})')
    typer.echo(f'Region  : {info.region}')
    typer.echo(f'State   : {info.state.value}')


def _create_podman(region, instance_type, max_hours, name):
    from sg_compute_specs.podman.schemas.Schema__Podman__Create__Request    import Schema__Podman__Create__Request
    from sg_compute_specs.podman.service.Podman__Service                    import Podman__Service
    svc   = Podman__Service().setup()
    sname = name or svc.name_gen.generate()
    req   = Schema__Podman__Create__Request(instance_type=instance_type, max_hours=max_hours)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create_stack(req)
    info  = resp.stack_info
    typer.echo(f'Created : {info.stack_name}')
    typer.echo(f'Instance: {info.instance_id}  ({info.instance_type})')
    typer.echo(f'Region  : {info.region}')
    typer.echo(f'State   : {info.state.value}')
