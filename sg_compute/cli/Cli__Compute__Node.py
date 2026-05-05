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
    node = _platform().get_node(node_id, region)
    if node is None:
        typer.echo(f'Node {node_id!r} not found in {region}', err=True)
        raise typer.Exit(1)
    render_node_info(node, Console(highlight=False, width=200))


@app.command()
def delete(node_id: str = typer.Argument(..., help='Node identifier (stack name).'),
           region : str  = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           yes    : bool = typer.Option(False,           '--yes',    '-y', help='Skip confirmation.')):
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
    _DISPATCHERS = {
        'docker'     : lambda: _create_docker     (region, instance_type, max_hours, registry, api_key, name),
        'podman'     : lambda: _create_podman     (region, instance_type, max_hours, name),
        'vnc'        : lambda: _create_vnc        (region, instance_type, max_hours, name),
        'elastic'    : lambda: _create_elastic    (region, instance_type, max_hours, name),
        'opensearch' : lambda: _create_opensearch (region, instance_type, max_hours, name),
        'neko'       : lambda: _create_neko       (region, instance_type, max_hours, name),
        'prometheus' : lambda: _create_prometheus (region, instance_type, max_hours, name),
        'ollama'     : lambda: _create_ollama     (region, instance_type, max_hours, name),
        'open_design': lambda: _create_open_design(region, instance_type, max_hours, name),
        'firefox'    : lambda: _create_firefox    (region, instance_type, max_hours, name),
    }
    fn = _DISPATCHERS.get(spec_id)
    if fn is None:
        supported = ', '.join(sorted(_DISPATCHERS))
        typer.echo(f'Unknown spec {spec_id!r}. Supported: {supported}', err=True)
        raise typer.Exit(1)
    fn()


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


def _echo_stack_info(info):
    typer.echo(f'Created : {info.stack_name}')
    typer.echo(f'Instance: {info.instance_id}  ({info.instance_type})')
    typer.echo(f'Region  : {info.region}')
    typer.echo(f'State   : {info.state}')


def _create_vnc(region, instance_type, max_hours, name):
    from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Create__Request   import Schema__Vnc__Stack__Create__Request
    from sg_compute_specs.vnc.service.Vnc__Service                          import Vnc__Service
    svc   = Vnc__Service().setup()
    sname = name or svc.name_gen.generate()
    req   = Schema__Vnc__Stack__Create__Request(instance_type=instance_type, max_hours=max_hours)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create_stack(req)
    typer.echo(f'Created : {resp.stack_name}')
    typer.echo(f'Instance: {resp.instance_id}  ({resp.instance_type})')
    typer.echo(f'Region  : {resp.region}')
    typer.echo(f'State   : {resp.state.value}')


def _create_elastic(region, instance_type, max_hours, name):
    from sg_compute_specs.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
    from sg_compute_specs.elastic.service.Elastic__Service                  import Elastic__Service
    svc   = Elastic__Service().setup()
    sname = name or svc._random_stack_name()
    req   = Schema__Elastic__Create__Request(instance_type=instance_type, max_hours=max_hours)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create(req)
    typer.echo(f'Created : {resp.stack_name}')
    typer.echo(f'Instance: {resp.instance_id}  ({resp.instance_type})')
    typer.echo(f'Region  : {resp.region}')
    typer.echo(f'State   : {resp.state.value}')


def _create_opensearch(region, instance_type, max_hours, name):
    from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
    from sg_compute_specs.opensearch.service.OpenSearch__Service                import OpenSearch__Service
    svc   = OpenSearch__Service().setup()
    sname = name or f'os-{svc.name_gen.generate()}'
    req   = Schema__OS__Stack__Create__Request(instance_type=instance_type, max_hours=max_hours)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create_stack(req)
    typer.echo(f'Created : {resp.stack_name}')
    typer.echo(f'Instance: {resp.instance_id}  ({resp.instance_type})')
    typer.echo(f'Region  : {resp.region}')
    typer.echo(f'State   : {resp.state.value}')


def _create_neko(region, instance_type, max_hours, name):                    # neko has no max_hours param
    from sg_compute_specs.neko.schemas.Schema__Neko__Stack__Create__Request  import Schema__Neko__Stack__Create__Request
    from sg_compute_specs.neko.service.Neko__Service                         import Neko__Service
    svc   = Neko__Service().setup()
    sname = name or f'neko-{svc.name_gen.generate()}'
    req   = Schema__Neko__Stack__Create__Request(instance_type=instance_type)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create_stack(req)
    typer.echo(f'Created : {resp.stack_name}')
    typer.echo(f'Instance: {resp.instance_id}  ({resp.instance_type})')
    typer.echo(f'Region  : {resp.region}')
    typer.echo(f'State   : {resp.state.value}')


def _create_prometheus(region, instance_type, max_hours, name):
    from sg_compute_specs.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
    from sg_compute_specs.prometheus.service.Prometheus__Service                  import Prometheus__Service
    svc   = Prometheus__Service().setup()
    sname = name or f'prom-{svc.name_gen.generate()}'
    req   = Schema__Prom__Stack__Create__Request(instance_type=instance_type, max_hours=max_hours)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create_stack(req)
    typer.echo(f'Created : {resp.stack_name}')
    typer.echo(f'Instance: {resp.instance_id}  ({resp.instance_type})')
    typer.echo(f'Region  : {resp.region}')
    typer.echo(f'State   : {resp.state.value}')


def _create_ollama(region, instance_type, max_hours, name):
    from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request     import Schema__Ollama__Create__Request
    from sg_compute_specs.ollama.service.Ollama__Service                     import Ollama__Service
    svc   = Ollama__Service().setup()
    sname = name or svc.name_gen.generate()
    req   = Schema__Ollama__Create__Request(stack_name    = sname         ,
                                             region        = region        ,
                                             instance_type = instance_type ,
                                             max_hours     = max_hours     )
    resp  = svc.create_stack(req)
    info  = resp.stack_info
    typer.echo(f'Created : {info.stack_name}')
    typer.echo(f'Instance: {info.instance_id}  ({info.instance_type})')
    typer.echo(f'Region  : {info.region}')
    typer.echo(f'State   : {info.state}')


def _create_open_design(region, instance_type, max_hours, name):
    from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Request import Schema__Open_Design__Create__Request
    from sg_compute_specs.open_design.service.Open_Design__Service                 import Open_Design__Service
    svc   = Open_Design__Service().setup()
    sname = name or svc.name_gen.generate()
    req   = Schema__Open_Design__Create__Request(stack_name    = sname         ,
                                                  region        = region        ,
                                                  instance_type = instance_type ,
                                                  max_hours     = max_hours     )
    resp  = svc.create_stack(req)
    info  = resp.stack_info
    typer.echo(f'Created : {info.stack_name}')
    typer.echo(f'Instance: {info.instance_id}  ({info.instance_type})')
    typer.echo(f'Region  : {info.region}')
    typer.echo(f'State   : {info.state}')


def _create_firefox(region, instance_type, max_hours, name):
    from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
    from sg_compute_specs.firefox.service.Firefox__AWS__Client                    import FIREFOX_NAMING
    from sg_compute_specs.firefox.service.Firefox__Service                        import Firefox__Service
    svc   = Firefox__Service().setup()
    sname = name or FIREFOX_NAMING.generate()
    req   = Schema__Firefox__Stack__Create__Request(instance_type=instance_type)
    req.stack_name.__init__(sname)
    req.region.__init__(region)
    resp  = svc.create_stack(req)
    typer.echo(f'Created : {resp.stack_name}')
    typer.echo(f'Instance: {resp.instance_id}  ({resp.instance_type})')
    typer.echo(f'Region  : {resp.region}')
    typer.echo(f'State   : {resp.state.value}')
