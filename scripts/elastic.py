# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — elastic.py
# CLI entry-point: sp elastic   (hidden alias: sp el)
# Manage ephemeral Elasticsearch + Kibana EC2 stacks. One EC2 instance hosts
# both services (single-node ES + Kibana behind nginx-TLS on :443). Lifecycle:
# create → wait → seed → delete.
#
# This module is the thin Typer wrapper. All logic lives in Elastic__Service —
# the CLI only constructs the service, calls one method, and renders the
# result via Rich tables.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Request    import Schema__Elastic__Seed__Request
from sgraph_ai_service_playwright__cli.elastic.service.AWS__Error__Translator       import AWS__Error__Translator
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service


DEBUG_TRACE = False                                                                 # Toggled by the --debug callback below; aws_error_handler reads this on each error


app = typer.Typer(help='Ephemeral Elasticsearch + Kibana EC2 stacks (single-node, MB-scale).',
                  no_args_is_help=True)


@app.callback()
def _elastic_root(debug: bool = typer.Option(False, '--debug',
                                              help='Show the full Python traceback on errors. Off by default — friendly one-line summary only.')):
    """Manage ephemeral Elastic+Kibana stacks. Pass --debug before a sub-command to get full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def build_service() -> Elastic__Service:                                            # Single construction site so tests can swap with __In_Memory subclass
    return Elastic__Service()


def resolve_stack_name(service   : Elastic__Service ,                               # Pick a stack name when the user didn't pass one: 0 → exit, 1 → auto-use, N → prompt
                       provided  : Optional[str]    ,
                       region    : Optional[str]    ,
                       prompt_fn = None                                              # Tests inject a fake for the multi-stack branch; defaults to typer.prompt
                       ) -> str:
    if provided:
        return provided
    listing = service.list_stacks(region=region or '')
    names   = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or 'the current region'

    if len(names) == 0:
        err = Console(highlight=False, stderr=True)
        err.print(f'\n  [yellow]No elastic stacks in {region_label}.[/]  Run: [bold]sp elastic create[/]\n')
        raise typer.Exit(1)

    if len(names) == 1:
        Console(highlight=False).print(f'\n  [dim]One stack found — using [bold]{names[0]}[/][/]')
        return names[0]

    c = Console(highlight=False)
    c.print(f'\n  [bold]Multiple stacks in {region_label}:[/]')
    for idx, name in enumerate(names, start=1):
        c.print(f'    {idx}. {name}')
    if prompt_fn is None:
        prompt_fn = lambda: typer.prompt('\n  Pick a stack number', type=int)
    raw = prompt_fn()
    try:
        choice = int(raw)
    except (TypeError, ValueError):
        choice = -1
    if choice < 1 or choice > len(names):
        Console(highlight=False, stderr=True).print(f'\n  [red]Invalid selection: {raw}[/]\n')
        raise typer.Exit(1)
    return names[choice - 1]


def aws_error_handler(fn):                                                          # Wraps every command so AWS-side failures render friendly text; surprises still re-raise
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            hint    = AWS__Error__Translator().translate(exc)
            console = Console(highlight=False, stderr=True)
            console.print()
            if hint.recognised:                                                     # Known AWS-side problem class — friendly headline + hints
                console.print(f'  [red]✗[/]  [bold]{str(hint.headline)}[/]')
                console.print(f'     {str(hint.body)}')
                for action in hint.hints:
                    console.print(f'     [dim]›[/] {action}')
                exit_code = int(hint.exit_code)
            else:                                                                   # Unknown — print compact type+message; full trace only with --debug
                console.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
                if not DEBUG_TRACE:
                    console.print('     [dim]› Re-run with [bold]sp elastic --debug ...[/] (or [bold]sp el --debug ...[/]) to see the full Python traceback.[/]')
                exit_code = 2
            if DEBUG_TRACE:                                                         # Same flag for both branches — caller asked for the trace, show it
                console.print()
                console.print('[dim]── traceback ──────────────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(exit_code)
    return wrapped


# ── create ─────────────────────────────────────────────────────────────────────

@app.command('create')
@aws_error_handler
def cmd_create(stack_name   : Optional[str] = typer.Argument (None,           help='Stack name (auto-generated if omitted: elastic-{adj}-{scientist}).'),
               region       : Optional[str] = typer.Option   (None, '--region',  help='AWS region (defaults to AWS_Config session region).'),
               instance_type: Optional[str] = typer.Option   (None, '--instance-type', help='EC2 instance type (default t3.medium).'),
               from_ami     : Optional[str] = typer.Option   (None, '--from-ami', help='AMI id (defaults to latest AL2023 via SSM).')):
    """Launch a new ephemeral Elastic+Kibana EC2 stack. Prints ELASTIC_PASSWORD once."""
    service = build_service()
    request = Schema__Elastic__Create__Request(stack_name    = stack_name    or '' ,
                                               region        = region        or '' ,
                                               instance_type = instance_type or '' ,
                                               from_ami      = from_ami      or '' )
    response = service.create(request)
    c = Console(highlight=False)
    c.print()
    c.print(f'  [bold]Stack launched[/]  [dim](state: {response.state})[/]')
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('stack-name'   , str(response.stack_name      ))
    t.add_row('aws-name'     , str(response.aws_name_tag    ))
    t.add_row('instance-id'  , str(response.instance_id     ))
    t.add_row('region'       , str(response.region          ))
    t.add_row('instance-type', str(response.instance_type   ))
    t.add_row('ami'          , str(response.ami_id          ))
    t.add_row('security-grp' , str(response.security_group_id))
    t.add_row('caller-ip'    , f'{str(response.caller_ip)}/32 (ingress on :443)')
    t.add_row('elastic-user' , str(response.elastic_username))
    t.add_row('elastic-pass' , str(response.elastic_password))
    c.print(t)
    c.print()
    c.print('  [bold]Next steps[/]:')
    c.print(f'    export SG_ELASTIC_PASSWORD={str(response.elastic_password)}')
    c.print(f'    sp elastic wait {str(response.stack_name)}        [dim]# poll until Kibana is ready[/]')
    c.print(f'    sp elastic seed {str(response.stack_name)}        [dim]# bulk-load 10k synthetic log docs[/]')
    c.print()


# ── list ───────────────────────────────────────────────────────────────────────

@app.command('list')
@aws_error_handler
def cmd_list(region: Optional[str] = typer.Option(None, '--region')):
    """List ephemeral elastic stacks in a region."""
    service = build_service()
    response = service.list_stacks(region=region or '')
    c = Console(highlight=False)
    if len(response.stacks) == 0:
        c.print(f'\n  [dim]No elastic stacks in {str(response.region)}.[/]  Run: [bold]sp elastic create[/]\n')
        return
    t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    t.add_column('Stack',        style='bold')
    t.add_column('Instance')
    t.add_column('State')
    t.add_column('Public IP')
    t.add_column('Kibana URL', style='dim')
    for info in response.stacks:
        t.add_row(str(info.stack_name)   ,
                  str(info.instance_id)  ,
                  str(info.state)        ,
                  str(info.public_ip) or '—',
                  str(info.kibana_url) or '—')
    c.print()
    c.print(t)
    c.print(f'\n  [dim]region: {str(response.region)} — {len(response.stacks)} stack(s)[/]\n')


# ── info ───────────────────────────────────────────────────────────────────────

@app.command('info')
@aws_error_handler
def cmd_info(stack_name: Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             region    : Optional[str] = typer.Option  (None, '--region')):
    """Show full details for a single stack. Does NOT include the elastic password."""
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    info    = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                     region     = region or '')
    c = Console(highlight=False)
    c.print()
    c.print(f'  [bold]Stack:[/] {str(info.stack_name)}  [dim](state: {info.state})[/]')
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('aws-name'     , str(info.aws_name_tag    ) or '—')
    t.add_row('instance-id'  , str(info.instance_id     ) or '—')
    t.add_row('region'       , str(info.region          ) or '—')
    t.add_row('instance-type', str(info.instance_type   ) or '—')
    t.add_row('ami'          , str(info.ami_id          ) or '—')
    t.add_row('security-grp' , str(info.security_group_id) or '—')
    t.add_row('allowed-ip'   , f'{str(info.allowed_ip)}/32' if str(info.allowed_ip) else '—')
    t.add_row('public-ip'    , str(info.public_ip       ) or '—')
    t.add_row('kibana-url'   , str(info.kibana_url      ) or '—')
    c.print(t)
    c.print()


# ── wait ───────────────────────────────────────────────────────────────────────

@app.command('wait')
@aws_error_handler
def cmd_wait(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             timeout    : int           = typer.Option (600, '--timeout', help='Max total wait in seconds. Polling interval is --poll-seconds.'),
             poll_seconds: int          = typer.Option (10, '--poll-seconds', help='Seconds between polls (default 10).'),
             region     : Optional[str] = typer.Option (None, '--region')):
    """Poll until Kibana returns HTTP 200. Live status: connection / nginx / Kibana."""
    from rich.status                                                                import Status
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    c          = Console(highlight=False)
    c.print(f'\n  [bold]Waiting for stack[/] [cyan]{stack_name}[/]  '
            f'[dim](polling every {poll_seconds}s, up to {timeout}s total)[/]')
    status = Status('initialising probe...', console=c, spinner='dots')
    status.start()
    try:
        def on_tick(tick):
            ip      = str(tick.info.public_ip) or '—'
            state   = str(tick.info.state)
            secs    = tick.elapsed_ms // 1000
            status.update(f'[dim][{secs:>3}s  #{tick.attempt:02d}][/]  '
                          f'state=[bold]{state}[/]  ip={ip}  '
                          f'probe=[bold]{tick.probe}[/]  — {tick.message}')
        info = service.wait_until_ready(stack_name  = Safe_Str__Elastic__Stack__Name(stack_name),
                                        region      = region or ''                              ,
                                        timeout     = timeout                                   ,
                                        poll_seconds= poll_seconds                              ,
                                        on_progress = on_tick                                   )
    finally:
        status.stop()
    if str(info.state) == 'ready':
        c.print(f'  ✅  Kibana is ready at [bold]{str(info.kibana_url)}[/]\n')
    else:
        c.print(f'  ❌  Stack {stack_name} not ready (state: {info.state})  '
                f'[dim]— re-run `sp elastic wait` or `sp elastic info` for details[/]\n')


# ── delete ─────────────────────────────────────────────────────────────────────

@app.command('delete')
@aws_error_handler
def cmd_delete(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
               region     : Optional[str] = typer.Option (None, '--region')):
    """Terminate the EC2 instance and best-effort delete its security group."""
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    response = service.delete_stack(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                    region     = region or '')
    c = Console(highlight=False)
    if len(response.terminated_instance_ids) == 0:
        c.print(f'\n  [yellow]No such stack:[/] {stack_name}\n')
        return
    c.print(f'\n  ✅  Terminated [bold]{stack_name}[/] — instance {str(response.target)}'
            f'  [dim](sg-deleted: {response.security_group_deleted})[/]\n')


# ── seed ───────────────────────────────────────────────────────────────────────

@app.command('connect')
@aws_error_handler
def cmd_connect(stack_name: Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                region    : Optional[str] = typer.Option (None, '--region')):
    """Open an interactive SSM shell on the EC2 host (no SSH/key-pair needed)."""
    import os
    import shutil
    import subprocess
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, region)
    info       = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                        region     = region or '')
    c = Console(highlight=False)
    if not str(info.instance_id):
        c.print(f'\n  [yellow]No such stack:[/] {stack_name}\n')
        raise typer.Exit(1)

    plugin_path = (shutil.which('session-manager-plugin') or
                   '/usr/local/sessionmanagerplugin/bin/session-manager-plugin')
    if not os.path.isfile(plugin_path):
        c.print('\n  [red]✗  session-manager-plugin not found in PATH.[/]')
        c.print('  Fix with one of:')
        c.print('    [bold]sudo ln -s /usr/local/sessionmanagerplugin/bin/session-manager-plugin /usr/local/bin/session-manager-plugin[/]')
        c.print('    [bold]brew install --cask session-manager-plugin[/]\n')
        raise typer.Exit(1)

    c.print(f'\n  🔌  Opening SSM session → [bold]{stack_name}[/] [dim]({info.instance_id})[/]\n')
    args = ['aws', 'ssm', 'start-session', '--target', str(info.instance_id)]
    if str(info.region):
        args += ['--region', str(info.region)]
    result = subprocess.run(args, check=False, capture_output=False)
    if result.returncode != 0:
        c.print(f'\n  [red]✗  Session ended with code {result.returncode}.[/]')
        c.print('  [dim]If you saw "Standard_Stream not found", run: brew reinstall --cask session-manager-plugin[/]\n')


@app.command('exec', context_settings={'allow_extra_args': True, 'ignore_unknown_options': True})
@aws_error_handler
def cmd_exec(ctx        : typer.Context                                                       ,
             first      : str           = typer.Argument(...,  help='Stack name OR start of the shell command (when only one stack exists).'),
             cmd        : Optional[str] = typer.Option(None, '--cmd',                          help='Shell command (alternative to positional).'),
             region     : Optional[str] = typer.Option(None, '--region')                      ,
             timeout    : int           = typer.Option(60,   '--timeout',                      help='Seconds to wait for the command to complete (min 30).')):
    """Run a shell command on the EC2 host via SSM and print stdout/stderr.

    Usage:
      sp elastic exec "docker ps"                   # auto-pick stack, run command
      sp elastic exec elastic-foo "docker ps"       # explicit stack + command
      sp elastic exec --cmd "uptime"                # auto-pick stack, command via flag
    """
    import shlex
    extra   = ctx.args or []
    service = build_service()
    listing = service.list_stacks(region=region or '')
    names   = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]

    if cmd is not None:                                                             # --cmd supplied → first is the stack name (or empty for auto-pick)
        stack_name = first if first else None
        shell_cmd  = cmd
    elif extra:                                                                     # positional command after first; first might be a stack name OR command word
        if first in names:
            stack_name = first
            shell_cmd  = shlex.join(extra)
        else:
            stack_name = None
            shell_cmd  = shlex.join([first] + extra)
    else:                                                                           # only `first` — treat as command, auto-pick stack
        stack_name = None
        shell_cmd  = first

    stack_name = resolve_stack_name(service, stack_name, region)
    if not shell_cmd:
        raise typer.BadParameter('Provide a shell command.')

    c = Console(highlight=False)
    c.print(f'\n  💻  [bold]{stack_name}[/]  [dim]$ {shell_cmd}[/]')
    result = service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                     command    = shell_cmd                                  ,
                                     region     = region or ''                               ,
                                     timeout    = timeout                                    )
    if str(result.stdout).strip():
        print(str(result.stdout).rstrip())
    if str(result.stderr).strip():
        import sys as _sys
        print(str(result.stderr).rstrip(), file=_sys.stderr)
    if not str(result.stdout).strip() and not str(result.stderr).strip():
        c.print('  [dim](no output)[/]')
    c.print(f'  [dim]→ status={result.status}  exit={result.exit_code}  duration={result.duration_ms}ms[/]\n')


@app.command('seed')
@aws_error_handler
def cmd_seed(stack_name : Optional[str] = typer.Argument(None, help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
             docs       : int           = typer.Option  (10_000, '--docs',        help='Document count (default 10000).'),
             index      : str           = typer.Option  ('sg-synthetic', '--index'),
             window_days: int           = typer.Option  (7,    '--window-days',  help='Spread timestamps over the last N days.'),
             batch_size : int           = typer.Option  (1_000,'--batch-size'),
             password   : Optional[str] = typer.Option  (None, '--password',     help='Elastic password (else $SG_ELASTIC_PASSWORD).')):
    """Generate and bulk-post synthetic log documents to the stack's Elastic."""
    service    = build_service()
    stack_name = resolve_stack_name(service, stack_name, None)
    request = Schema__Elastic__Seed__Request(stack_name       = Safe_Str__Elastic__Stack__Name(stack_name),
                                             index            = index                                     ,
                                             document_count   = docs                                      ,
                                             window_days      = window_days                               ,
                                             elastic_password = Safe_Str__Elastic__Password(password) if password else Safe_Str__Elastic__Password(''),
                                             batch_size       = batch_size                                )
    response = service.seed_stack(request)
    c = Console(highlight=False)
    if response.documents_posted == 0 and response.documents_failed == 0:
        c.print(f'\n  [yellow]Nothing seeded — stack has no public IP yet:[/] {stack_name}\n')
        return
    c.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style='dim', justify='right')
    t.add_column(style='bold')
    t.add_row('stack',     str(response.stack_name      ))
    t.add_row('index',     str(response.index           ))
    t.add_row('posted',    str(response.documents_posted))
    t.add_row('failed',    str(response.documents_failed))
    t.add_row('batches',   str(response.batches         ))
    t.add_row('duration',  f'{response.duration_ms} ms')
    t.add_row('rate',      f'{response.docs_per_second} docs/sec')
    c.print(t)
    c.print()
