# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — local-claude: Cli__Local_Claude
# Builder-driven CLI; declares local-claude extras and the create-time field
# setter. The 8 standard verbs (list/info/create/wait/health/connect/
# exec/delete) plus the ami sub-typer come from Spec__CLI__Builder.
# Spec-specific extras:
#   - models  : list models served by the running vLLM container
#   - logs    : stream docker logs from vllm-claude-code
#   - claude  : SSM-attach (user runs ~/local-llm-claude.sh inside)
# ═══════════════════════════════════════════════════════════════════════════════

import os

import typer
from rich.console import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults     import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors       import spec_cli_errors
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Create__Request import Schema__Local_Claude__Create__Request
from sg_compute_specs.local_claude.service.Local_Claude__Service                 import Local_Claude__Service


def _set_extras(request, model='', served_model_name='', tool_parser='',
                disk_size=0, with_claude_code=True, with_sgit=True, use_spot=True,
                max_model_len=0, kv_cache_dtype='', gpu_memory_utilization=0.0):
    if model:
        request.model                  = model
    if served_model_name:
        request.served_model_name      = served_model_name
    if tool_parser:
        request.tool_parser            = tool_parser
    if disk_size:
        request.disk_size_gb           = int(disk_size)
    if max_model_len:
        request.max_model_len          = int(max_model_len)
    if kv_cache_dtype:
        request.kv_cache_dtype         = kv_cache_dtype
    if gpu_memory_utilization:
        request.gpu_memory_utilization = float(gpu_memory_utilization)
    request.with_claude_code           = bool(with_claude_code)
    request.with_sgit                  = bool(with_sgit)
    request.use_spot                   = bool(use_spot)


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'local-claude'                              ,
    display_name          = 'Local Claude'                              ,
    default_instance_type = 'g5.xlarge'                                 ,
    create_request_cls    = Schema__Local_Claude__Create__Request        ,
    service_factory       = lambda: Local_Claude__Service().setup()     ,
    health_path           = '/v1/models'                                ,
    health_port           = 8000                                        ,
    health_scheme         = 'http'                                      ,
    extra_create_field_setters = _set_extras                            ,
)


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('model'            , str , 'QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ',
         'HF model reference (org/repo format).'),
        ('served_model_name', str , 'local-coder',
         'Alias vLLM serves; must match ANTHROPIC_MODEL in the launcher.'),
        ('tool_parser'      , str , 'qwen3_coder',
         'vLLM tool-call parser. qwen3_coder is the verified-working choice for Qwen3-Coder.'),
        ('disk_size'        , int , 200,
         'Root volume in GiB. 200 GiB default; HF cache + Docker images need room.'),
        ('with_claude_code' , bool, True,
         'Install Claude Code on first boot via Anthropic official installer.'),
        ('with_sgit'        , bool, True,
         'Install sgit in a python3.12 venv for encrypted vault storage.'),
        ('use_spot'         , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        ('max_model_len'         , int  , 65536,
         'Maximum sequence length. Lower to 49152/32768 on smaller GPUs.'),
        ('kv_cache_dtype'        , str  , 'fp8',
         'KV-cache precision. fp8 halves VRAM use vs auto (FP16).'),
        ('gpu_memory_utilization', float, 0.92,
         'Fraction of GPU VRAM vLLM may allocate (0.0-1.0).'),
    ],
).build()


# ── local-claude-specific extras ──────────────────────────────────────────────

@app.command()
@spec_cli_errors
def models(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List models served by the running vLLM container."""
    svc    = Local_Claude__Service().setup()
    name   = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'local-claude')
    result = svc.exec(region, name, 'curl -s http://127.0.0.1:8000/v1/models | jq .', timeout_sec=15)
    Console(highlight=False).print(str(getattr(result, 'stdout', '')))


@app.command()
@spec_cli_errors
def logs(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         tail  : int = typer.Option(100, '--tail', '-n', help='Number of log lines to fetch.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Stream recent docker logs from the vllm-claude-code container."""
    svc    = Local_Claude__Service().setup()
    name   = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'local-claude')
    result = svc.exec(region, name, f'docker logs --tail {tail} vllm-claude-code 2>&1', timeout_sec=20)
    Console(highlight=False).print(str(getattr(result, 'stdout', '')))


@app.command()
@spec_cli_errors
def claude(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Open an SSM session to the stack. Run ~/local-llm-claude.sh inside."""
    svc         = Local_Claude__Service().setup()
    name        = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'local-claude')
    instance_id = svc.claude_session(region, name)
    Console(highlight=False).print(
        f'  [dim]Connecting to {name} ({instance_id}); '
        f'inside the shell run [bold]~/local-llm-claude.sh[/][/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session',
                       '--target', instance_id, '--region', region])
