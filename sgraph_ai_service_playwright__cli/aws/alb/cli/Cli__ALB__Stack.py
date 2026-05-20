# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Cli__ALB__Stack
# Typer CLI surface for `sg aws alb stack *` commands.
#
# Command tree:
#   sg aws alb stack provision --name NAME --vpc VPC_ID --subnets SN1,SN2
#                              [--target-type instance] [--yes] [--json]
#                              (mutation-gated)
#   sg aws alb stack destroy   <stack-name> [--yes] [--json] (mutation-gated)
#   sg aws alb stack describe  <stack-name> [--json]
#
# Mutations require SG_AWS__ALB__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                              import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate       import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__AWS__Client  import ALB__AWS__Client
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__Stack__Provisioner import ALB__Stack__Provisioner
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Stack__Request import Schema__ALB__Stack__Request


_MUTATION_ENV = 'SG_AWS__ALB__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='stack', help='ALB stack operations.', no_args_is_help=True)


@app.callback()
def _setup_ctx(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('alb_client', ALB__AWS__Client())


def _report_to_dict(report) -> dict:
    phases = []
    for p in (report.phases or []):
        phases.append({'name': str(p.name), 'status': str(p.status) if p.status else '',
                       'duration_ms': int(p.duration_ms), 'detail': str(p.detail)})
    return dict(
        operation       = str(report.operation),
        stack_name      = str(report.stack_name),
        ok              = bool(report.ok),
        total_ms        = int(report.total_ms),
        lb_arn          = str(report.lb_arn),
        lb_dns_name     = str(report.lb_dns_name),
        tg_arn          = str(report.tg_arn),
        listener_arn    = str(report.listener_arn),
        alb_sg_id       = str(report.alb_sg_id),
        target_sg_id    = str(report.target_sg_id),
        phases          = phases,
        error           = str(report.error),
        rollback_errors = [str(e) for e in (report.rollback_errors or [])],
    )


def _render_report(report) -> None:
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18)
    t.add_column()
    t.add_row('stack',       str(report.stack_name))
    t.add_row('lb arn',      str(report.lb_arn) or '—')
    t.add_row('lb dns',      str(report.lb_dns_name) or '—')
    t.add_row('tg arn',      str(report.tg_arn) or '—')
    t.add_row('listener',    str(report.listener_arn) or '—')
    t.add_row('alb sg',      str(report.alb_sg_id) or '—')
    t.add_row('target sg',   str(report.target_sg_id) or '—')
    t.add_row('total ms',    str(report.total_ms))
    ok_label = '[green]ok[/green]' if report.ok else '[red]failed[/red]'
    t.add_row('status',      ok_label)
    console.print()
    console.print(t)
    console.print()


# ── provision ─────────────────────────────────────────────────────────────────

@app.command('provision')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def stack_provision(ctx         : typer.Context,
                    name        : str  = typer.Option(..., '--name',        help='Stack name.'),
                    vpc         : str  = typer.Option(..., '--vpc',         help='VPC ID.'),
                    subnets     : str  = typer.Option(..., '--subnets',     help='Comma-separated subnet IDs (2 required).'),
                    target_type : str  = typer.Option('instance', '--target-type',
                                                       help='instance | ip'),
                    lb_port     : int  = typer.Option(80,   '--lb-port',    help='ALB listener port.'),
                    target_port : int  = typer.Option(8080, '--target-port', help='Target port.'),
                    yes         : bool = typer.Option(False, '--yes',       help='Skip confirmation.'),
                    as_json     : bool = typer.Option(False, '--json',      help='Output as JSON.')):
    """Provision a full ALB stack (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str import List__Str
    client     = ctx.obj['alb_client']
    subnet_ids = List__Str()
    for s in subnets.split(','):
        s_clean = s.strip()
        if s_clean:
            subnet_ids.append(s_clean)
    if not yes and not typer.confirm(f'Provision ALB stack {name!r} in VPC {vpc}?', default=True):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type import Enum__ALB__Target_Type
    try:
        tgt_type_enum = Enum__ALB__Target_Type(target_type)
    except ValueError:
        tgt_type_enum = Enum__ALB__Target_Type.INSTANCE
    request = Schema__ALB__Stack__Request(
        stack_name        = name,
        vpc_id            = vpc,
        subnet_ids        = subnet_ids,
        target_type       = tgt_type_enum,
        lb_port           = lb_port,
        target_port       = target_port,
        health_check_path = '/info/health',
    )
    provisioner = ALB__Stack__Provisioner(alb_client=client)
    report      = provisioner.create_stack(request)
    if as_json:
        typer.echo(json.dumps(_report_to_dict(report), indent=2))
        if not report.ok:
            raise typer.Exit(1)
        return
    _render_report(report)
    if not report.ok:
        console.print(f'[red]Stack provision failed:[/red] {report.error}')
        raise typer.Exit(1)


# ── destroy ───────────────────────────────────────────────────────────────────

@app.command('destroy')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def stack_destroy(ctx        : typer.Context,
                  stack_name : str  = typer.Argument(..., help='Stack name to destroy.'),
                  yes        : bool = typer.Option(False, '--yes',  help='Skip confirmation.'),
                  as_json    : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Destroy a named ALB stack (requires SG_AWS__ALB__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['alb_client']
    if not yes and not typer.confirm(f'Destroy ALB stack {stack_name!r}?', default=False):
        if as_json:
            typer.echo(json.dumps({'ok': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    provisioner = ALB__Stack__Provisioner(alb_client=client)
    report      = provisioner.delete_stack(stack_name)
    if as_json:
        typer.echo(json.dumps(_report_to_dict(report), indent=2))
        if not report.ok:
            raise typer.Exit(1)
        return
    _render_report(report)
    if not report.ok:
        console.print(f'[red]Stack destroy failed:[/red] {report.error}')
        raise typer.Exit(1)


# ── describe ──────────────────────────────────────────────────────────────────

@app.command('describe')
@spec_cli_errors
def stack_describe(ctx        : typer.Context,
                   stack_name : str  = typer.Argument(..., help='Stack name.'),
                   as_json    : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Describe the current resources of a named ALB stack."""
    client      = ctx.obj['alb_client']
    provisioner = ALB__Stack__Provisioner(alb_client=client)
    detail      = provisioner.describe_stack(stack_name)
    if detail is None:
        if as_json:
            typer.echo(json.dumps({'found': False, 'stack_name': stack_name}, indent=2))
        else:
            console.print(f'[yellow]No ALB stack found:[/yellow] {stack_name}')
        raise typer.Exit(1)
    payload = dict(
        found        = True,
        stack_name   = detail.stack_name,
        lb_arn       = detail.lb_arn,
        lb_dns_name  = detail.lb_dns_name,
        tg_arn       = detail.tg_arn,
        listener_arn = detail.listener_arn,
        alb_sg_id    = detail.alb_sg_id,
        target_sg_id = detail.target_sg_id,
    )
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16)
    t.add_column()
    t.add_row('stack',       payload['stack_name'])
    t.add_row('lb arn',      payload['lb_arn'] or '—')
    t.add_row('lb dns',      payload['lb_dns_name'] or '—')
    t.add_row('tg arn',      payload['tg_arn'] or '—')
    t.add_row('listener',    payload['listener_arn'] or '—')
    t.add_row('alb sg',      payload['alb_sg_id'] or '—')
    t.add_row('target sg',   payload['target_sg_id'] or '—')
    console.print()
    console.print(t)
    console.print()
