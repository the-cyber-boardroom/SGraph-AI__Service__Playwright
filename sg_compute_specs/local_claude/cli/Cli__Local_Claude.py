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
        ('disk_size'        , int , 200,
         'Root volume in GiB. 200 GiB default; HF cache + Docker images need room.'),
        ('with_claude_code' , bool, True,
         'Install Claude Code on first boot via Anthropic official installer.'),
        ('with_sgit'        , bool, True,
         'Install sgit in a python3.13 venv for encrypted vault storage.'),
        ('use_spot'         , bool, True,
         'Spot instance (~70% cheaper). Pass --no-use-spot for on-demand.'),
        # ── advanced: hidden from --help; still accepted; omitted from equivalent cmd when at default ──
        ('served_model_name'     , str  , 'local-coder'  ,
         'Alias vLLM serves; must match ANTHROPIC_MODEL in the launcher.'     , True),
        ('tool_parser'           , str  , 'qwen3_coder'  ,
         'vLLM tool-call parser. qwen3_coder works for Qwen3-Coder.'         , True),
        ('max_model_len'         , int  , 65536          ,
         'Maximum sequence length. Lower to 49152/32768 on smaller GPUs.'    , True),
        ('kv_cache_dtype'        , str  , 'fp8'          ,
         'KV-cache precision. fp8 halves VRAM use vs auto (FP16).'           , True),
        ('gpu_memory_utilization', float, 0.92           ,
         'Fraction of GPU VRAM vLLM may allocate (0.0-1.0).'                 , True),
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


_LOG_SOURCES = {                                                       # name → (shell command template, ssm timeout, one-line description)
    'vllm'      : ('docker logs --tail {tail} vllm-claude-code 2>&1' , 30,
                   'vLLM container (only ready after Docker pull + container start)'),
    'boot'      : ('tail -n {tail} /var/log/ephemeral-ec2-boot.log'  , 20,
                   'EC2 user-data boot script — available within seconds of launch'),
    'cloud-init': ('tail -n {tail} /var/log/cloud-init-output.log'   , 20,
                   'cloud-init full output — slightly behind boot log'),
    'docker'    : ('journalctl -u docker -n {tail} --no-pager'       , 20,
                   'docker daemon journal — only after Docker is installed'),
    'journal'   : ('journalctl -n {tail} --no-pager'                 , 30,
                   'full systemd journal — always available'),
}


def _prompt_for_source(c: Console) -> str:
    c.print()
    c.print('  [bold]Which log source?[/]')
    keys = list(_LOG_SOURCES)
    for i, k in enumerate(keys, 1):
        _, _, desc = _LOG_SOURCES[k]
        c.print(f'    [cyan]{i}[/]  [bold]{k:11}[/] [dim]{desc}[/]')
    c.print()
    ans = typer.prompt('  Pick a number or name', default='boot').strip()
    if ans.isdigit() and 1 <= int(ans) <= len(keys):
        return keys[int(ans) - 1]
    if ans in _LOG_SOURCES:
        return ans
    raise typer.BadParameter(f'unknown source {ans!r}; pick from: {", ".join(_LOG_SOURCES)}')


@app.command(help='''Stream logs from the stack.

\b
Available sources (pick with --source / -s, or omit to be prompted):
  vllm        vLLM container (only ready after Docker pull + container start)
  boot        EC2 user-data boot script — available within seconds of launch
  cloud-init  cloud-init full output — slightly behind boot log
  docker      docker daemon journal — only after Docker is installed
  journal     full systemd journal — always available
''')
@spec_cli_errors
def logs(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         tail  : int = typer.Option(300, '--tail', '-n', help='Number of log lines to fetch.'),
         source: str = typer.Option('', '--source', '-s',
                                    help='vllm | boot | cloud-init | docker | journal. Omit to be prompted.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c = Console(highlight=False)
    if not source:
        source = _prompt_for_source(c)
    if source not in _LOG_SOURCES:
        raise typer.BadParameter(
            f'unknown source {source!r}; pick from: {", ".join(_LOG_SOURCES)}')
    cmd_tpl, timeout, _desc = _LOG_SOURCES[source]
    svc    = Local_Claude__Service().setup()
    name   = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'local-claude')
    others = '  '.join(k for k in _LOG_SOURCES if k != source)
    c.print(f'  [bold]{source}[/] [dim]──  other sources: {others}[/]')
    c.print()
    result = svc.exec(region, name, cmd_tpl.format(tail=tail), timeout_sec=timeout)
    c.print(str(getattr(result, 'stdout', '')))


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


_DIAG_ICONS = {
    'ok'  : '[green]✓[/]',
    'fail': '[red]✗[/]',
    'warn': '[yellow]⚠[/]',
    'skip': '[dim]⊘[/]',
}

# per-check log sources to suggest when a check fails/warns
_DIAG_HINTS = {
    'boot-ok'       : [('boot'  , 'watch boot progress')],
    'boot-failed'   : [('boot'  , 'full boot log with error details')],
    'docker'        : [('docker', 'docker daemon startup'), ('boot', 'earlier boot errors')],
    'docker-access' : [('boot'  , 'check ssm-user / usermod step in boot log')],
    'vllm-container': [('boot'  , 'boot progress — docker pull is the long step'),
                       ('docker', 'docker daemon / pull errors')],
    'vllm-api'      : [('vllm'  , 'vLLM container output')],
    'ssm-reachable' : [('boot'  , 'see if boot completed at all')],
}


@app.command()
@spec_cli_errors
def diag(name  : str = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Run the sequential 9-step boot checklist and show which steps passed/failed.

    \b
    Steps checked in order:
      ec2-state       EC2 instance is in running state
      ssm-reachable   SSM exec can reach the instance
      boot-failed     /var/lib/sg-compute-boot-failed is absent
      boot-ok         /var/lib/sg-compute-boot-ok is present
      docker          Docker CE service is active
      docker-access   ssm-user can run docker without sudo
      gpu             nvidia-smi reports at least one GPU
      vllm-container  vllm-claude-code container is running
      vllm-api        vLLM /v1/models endpoint responds
    """
    import sys
    c      = Console(highlight=False)
    svc    = Local_Claude__Service().setup()
    name   = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'local-claude')
    c.print()
    c.print(f'  [bold]Diagnostics[/]  ·  [cyan]{name}[/]  [dim]{region}[/]')
    c.print()

    is_tty  = sys.stdout.isatty()
    results = []

    for check_name, status, detail in svc.diagnose(region, name):
        if status == 'checking':
            if is_tty:
                sys.stdout.write(f'  ···  {check_name:<20} checking…\r')
                sys.stdout.flush()
            continue

        # Erase the "checking…" line before printing the result.
        if is_tty:
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()

        icon = _DIAG_ICONS.get(status, '[dim]?[/]')
        results.append((check_name, status, detail))

        # Multi-line detail (e.g. boot log tail on failure): indent continuation lines.
        first_line, *rest = detail.split('\n')
        c.print(f'  {icon}  {check_name:20} [dim]{first_line}[/]')
        for extra in rest:
            if extra.strip():
                c.print(f'       [dim]{extra}[/]')

    c.print()
    failed = [n for n, s, _ in results if s == 'fail']
    warned = [n for n, s, _ in results if s == 'warn']
    if not failed and not warned:
        c.print('  [green]✓  all checks passed[/]')
    else:
        parts = []
        if failed: parts.append(f'[red]{len(failed)} failed[/]')
        if warned: parts.append(f'[yellow]{len(warned)} warnings[/]')
        c.print(f'  {", ".join(parts)}')
        # collect suggested log commands for actionable checks, deduplicated
        seen_sources   = set()
        suggested_cmds = []
        for check_name, status, _ in results:
            if status not in ('fail', 'warn'):
                continue
            for source, reason in _DIAG_HINTS.get(check_name, []):
                if source not in seen_sources:
                    seen_sources.add(source)
                    suggested_cmds.append((source, reason, check_name))
        if suggested_cmds:
            c.print()
            c.print('  [bold]Suggested next steps:[/]')
            for source, reason, origin in suggested_cmds:
                c.print(f'    [cyan]sg lc logs {name} --source {source:<12}[/]'
                        f'  [dim]# {reason}  ({origin})[/]')
        c.print()
        c.print('  [dim]Share the output above with the bot for diagnosis.[/]')
    c.print()
