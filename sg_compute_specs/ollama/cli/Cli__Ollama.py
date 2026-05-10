# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Ollama: Cli__Ollama
# Builder-driven CLI; declares ollama-specific extras and the create-time
# field setter. The 8 standard verbs (list/info/create/wait/health/connect/
# exec/delete) come from Spec__CLI__Builder; this file only adds:
#   - models : query the running stack for installed models
#   - pull   : pull a new model into a running stack
#   - claude : SSM-attach to the tmux 'claude' session
# ═══════════════════════════════════════════════════════════════════════════════

import os

import typer
from rich.console import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec  import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder       import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults      import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors        import spec_cli_errors
from sg_compute_specs.ollama.enums.Enum__Ollama__AMI__Base   import Enum__Ollama__AMI__Base
from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request import Schema__Ollama__Create__Request
from sg_compute_specs.ollama.service.Ollama__Service                  import Ollama__Service


def _set_extras(request, model='', ami_base='dlami', disk_size=0,
                with_claude=False, expose_api=False, use_spot=True):
    if model:
        request.model_name = model
    request.ami_base    = (Enum__Ollama__AMI__Base.AL2023 if ami_base == 'al2023'
                           else Enum__Ollama__AMI__Base.DLAMI)
    request.disk_size_gb = int(disk_size)
    request.with_claude  = bool(with_claude)
    request.expose_api   = bool(expose_api)
    request.use_spot     = bool(use_spot)


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'ollama'                          ,
    display_name          = 'Ollama'                          ,
    default_instance_type = 'g5.xlarge'                       ,
    create_request_cls    = Schema__Ollama__Create__Request    ,
    service_factory       = lambda: Ollama__Service().setup() ,
    health_path           = '/api/tags'                       ,
    health_port           = 11434                              ,
    health_scheme         = 'http'                             ,   # Ollama API is plain HTTP on 11434
    extra_create_field_setters = _set_extras                  ,
)


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('model'      , str , 'gpt-oss:20b', 'Ollama model reference (e.g. gpt-oss:20b, llama3.3).'),
        ('disk_size'  , int , 250          , 'Root volume in GiB. 250 GiB default; 0 = keep AMI default.'),
        ('use_spot'   , bool, True         , 'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        # ── advanced: hidden from --help; still accepted; omitted from equivalent cmd when at default ──
        ('ami_base'   , str , 'dlami'      , 'AMI base: dlami (default; GPU+drivers preinstalled) or al2023.'   , True),
        ('with_claude', bool, False        , 'Boot Claude integration under tmux (sudo -u ec2-user tmux new-session).', True),
        ('expose_api' , bool, False        , 'Bind ollama to 0.0.0.0:11434 (SG controls who can reach it).'     , True),
    ],
).build()


# ── ollama-specific extras ────────────────────────────────────────────────────

@app.command()
@spec_cli_errors
def models(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List installed models on a running ollama stack."""
    svc    = Ollama__Service().setup()
    name   = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'ollama')
    result = svc.exec(region, name, 'ollama list', timeout_sec=30)
    Console(highlight=False).print(str(getattr(result, 'stdout', '')))


@app.command()
@spec_cli_errors
def pull(model_name: str = typer.Argument(..., help='Ollama model reference to pull (e.g. gpt-oss:20b).'),
         name      : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region    : str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Pull a model into the running stack (long-running; uses 900s timeout)."""
    svc    = Ollama__Service().setup()
    name   = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'ollama')
    result = svc.pull_model(region, name, model_name)
    Console(highlight=False).print(str(getattr(result, 'stdout', '')))


@app.command()
@spec_cli_errors
def claude(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Open an SSM session to attach to the tmux 'claude' session."""
    svc         = Ollama__Service().setup()
    name        = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'ollama')
    instance_id = svc.claude_session(region, name)
    Console(highlight=False).print(
        f'  [dim]Connecting to {name} ({instance_id}); inside the shell run [bold]tmux attach -t claude[/][/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session',
                       '--target', instance_id, '--region', region])
