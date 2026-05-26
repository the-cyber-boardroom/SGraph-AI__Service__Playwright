# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Cli__Vscode
# Builder-driven CLI. The standard verbs (list/info/create/wait/health/connect/
# exec/delete) plus the ami/cert sub-typers come from Spec__CLI__Builder.
# Spec-specific extras:
#   - forward : open the editor via SSM port-forward (no inbound ports)
#   - url     : print the editor URL for a stack
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults     import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors       import spec_cli_errors

from sg_compute_specs.vscode.cli.Renderers                           import render_create, render_info
from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution        import Enum__Vscode__Distribution
from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress             import Enum__Vscode__Ingress
from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Request import Schema__Vscode__Create__Request
from sg_compute_specs.vscode.service.Vscode__Service                 import Vscode__Service
from sg_compute_specs.vscode.service.Vscode__Stack__Mapper           import EDITOR_PORT


def _set_extras(request, distribution='code-server', ingress='ssm-forward',
                disk_size=0, password='', public=False, use_spot=True):
    request.distribution   = Enum__Vscode__Distribution(distribution)
    request.ingress        = Enum__Vscode__Ingress(ingress)
    if disk_size:
        request.disk_size_gb = int(disk_size)
    if password:
        request.password = password
    request.public_ingress = bool(public)
    request.use_spot       = bool(use_spot)


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'vscode'                              ,
    display_name          = 'VS Code'                            ,
    default_instance_type = 't3.large'                            ,
    create_request_cls    = Schema__Vscode__Create__Request       ,
    service_factory       = lambda: Vscode__Service().setup()     ,
    health_path           = '/healthz'                            ,
    health_port           = EDITOR_PORT                           ,
    health_scheme         = 'http'                                ,
    render_info_fn        = render_info                           ,
    render_create_fn      = render_create                         ,
    extra_create_field_setters = _set_extras                      ,
)


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('distribution', str , 'code-server',
         'VS Code build: code-server (default) | openvscode-server | serve-web.'),
        ('ingress'     , str , 'ssm-forward',
         'Access mode: ssm-forward (default, no inbound ports) | public-https.'),
        ('disk_size'   , int , 100,
         'Root volume in GiB. Room for repos + node_modules + Docker images.'),
        ('password'    , str , '',
         'Editor password. Auto-generated and shown once if blank.'),
        ('public'      , bool, False,
         'PUBLIC_HTTPS only: open :443 to 0.0.0.0/0 instead of your caller /32.'),
        ('use_spot'    , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
    ],
).build()


# ── vscode-specific extras ──────────────────────────────────────────────────────

@app.command(help='''Open the editor via an SSM port-forward tunnel.

\b
Starts an `aws ssm start-session AWS-StartPortForwardingSession` tunnel to the
loopback-bound code-server, then hands the terminal to the aws CLI — Ctrl-C
closes the tunnel. Open the printed URL in your browser once the tunnel is up.
''')
@spec_cli_errors
def forward(name      : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
            local_port: int = typer.Option(EDITOR_PORT, '--local-port', '-p',
                                            help='Local port to bind the tunnel to.'),
            region    : str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c    = Console(highlight=False)
    svc  = Vscode__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vscode')
    info = svc.get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No vscode stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(getattr(info, 'instance_id', '') or '')
    if not iid:
        c.print(f'  [red]✗  {name!r} has no instance id yet[/]')
        raise typer.Exit(1)

    url = f'http://localhost:{local_port}'
    c.print()
    c.print('  [bold]Opening VS Code[/]  [dim]via SSM port-forward[/]')
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='dim', no_wrap=True, min_width=14)
    t.add_column()
    t.add_row('stack', f'[cyan]{name}[/]  [dim]{iid}[/]  region=[dim]{region}[/]')
    t.add_row('url',   f'[bold cyan]{url}[/]')
    t.add_row('',      '[dim]→ once you see "Waiting for connections…", open the url above. Ctrl-C closes the tunnel.[/]')
    c.print(t)
    c.print()

    parameters = json.dumps({'portNumber'      : [str(EDITOR_PORT)],
                             'localPortNumber' : [str(local_port)]})
    os.execvp('aws', [
        'aws', 'ssm', 'start-session',
        '--target',        iid,
        '--document-name', 'AWS-StartPortForwardingSession',
        '--parameters',    parameters,
        '--region',        region,
    ])


@app.command()
@spec_cli_errors
def url(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
        region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Print the editor URL for a stack."""
    svc  = Vscode__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'vscode')
    info = svc.get_stack_info(region, name)
    if info is None:
        Console(highlight=False, stderr=True).print(f'  [red]✗  No vscode stack matched {name!r}[/]')
        raise typer.Exit(1)
    Console(highlight=False).print(str(getattr(info, 'vscode_url', '') or ''))
