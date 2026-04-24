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


app = typer.Typer(help='Ephemeral Elasticsearch + Kibana EC2 stacks (single-node, MB-scale).',
                  no_args_is_help=True)


def build_service() -> Elastic__Service:                                            # Single construction site so tests can swap with __In_Memory subclass
    return Elastic__Service()


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
            hint = AWS__Error__Translator().translate(exc)
            if not hint.recognised:                                                 # Unknown exception — let Typer / Python show the trace
                raise
            console = Console(highlight=False, stderr=True)
            console.print()
            console.print(f'  [red]✗[/]  [bold]{str(hint.headline)}[/]')
            console.print(f'     {str(hint.body)}')
            for action in hint.hints:
                console.print(f'     [dim]›[/] {action}')
            console.print()
            raise typer.Exit(int(hint.exit_code))
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
def cmd_info(stack_name: str = typer.Argument(..., help='Stack name.'),
             region    : Optional[str] = typer.Option(None, '--region')):
    """Show full details for a single stack. Does NOT include the elastic password."""
    service = build_service()
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
def cmd_wait(stack_name : str           = typer.Argument(..., help='Stack name.'),
             timeout    : int           = typer.Option (600, '--timeout', help='Total seconds to wait (default 600).'),
             region     : Optional[str] = typer.Option (None, '--region')):
    """Poll until Kibana on the stack returns HTTP 200, or timeout."""
    service = build_service()
    c       = Console(highlight=False)
    c.print(f'\n  ⏳  Waiting for stack [bold]{stack_name}[/] (timeout {timeout}s)...')
    info = service.wait_until_ready(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                    region     = region or ''                              ,
                                    timeout    = timeout                                   )
    if str(info.state) == 'ready':
        c.print(f'  ✅  Kibana is ready at [bold]{str(info.kibana_url)}[/]\n')
    else:
        c.print(f'  ❌  Stack {stack_name} not ready (state: {info.state})\n')


# ── delete ─────────────────────────────────────────────────────────────────────

@app.command('delete')
@aws_error_handler
def cmd_delete(stack_name : str           = typer.Argument(..., help='Stack name.'),
               region     : Optional[str] = typer.Option (None, '--region')):
    """Terminate the EC2 instance and best-effort delete its security group."""
    service = build_service()
    response = service.delete_stack(stack_name = Safe_Str__Elastic__Stack__Name(stack_name),
                                    region     = region or '')
    c = Console(highlight=False)
    if len(response.terminated_instance_ids) == 0:
        c.print(f'\n  [yellow]No such stack:[/] {stack_name}\n')
        return
    c.print(f'\n  ✅  Terminated [bold]{stack_name}[/] — instance {str(response.target)}'
            f'  [dim](sg-deleted: {response.security_group_deleted})[/]\n')


# ── seed ───────────────────────────────────────────────────────────────────────

@app.command('seed')
@aws_error_handler
def cmd_seed(stack_name : str           = typer.Argument(...,  help='Stack name.'),
             docs       : int           = typer.Option (10_000, '--docs',        help='Document count (default 10000).'),
             index      : str           = typer.Option ('sg-synthetic', '--index'),
             window_days: int           = typer.Option (7,    '--window-days',  help='Spread timestamps over the last N days.'),
             batch_size : int           = typer.Option (1_000,'--batch-size'),
             password   : Optional[str] = typer.Option (None, '--password',     help='Elastic password (else $SG_ELASTIC_PASSWORD).')):
    """Generate and bulk-post synthetic log documents to the stack's Elastic."""
    service = build_service()
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
