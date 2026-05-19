# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate/cli — Cli__Vault_App__Fargate__Setup
# Typer CLI surface for `sg vault-app fargate setup *` commands.
#
# Command tree:
#   sg vault-app fargate setup check   [--cluster C] [--phase P] [--json]
#   sg vault-app fargate setup status  [--cluster C] [--json]
#   sg vault-app fargate setup create  [--cluster C] [--subnets S] [--sg G]
#                                      [--phase P] [--yes] [--time] [--json]
#   sg vault-app fargate setup update  [--cluster C] [--phase P] [--yes]
#                                      [--time] [--json]
#   sg vault-app fargate setup delete  [--cluster C] [--phase P] [--yes]
#                                      [--time] [--json]
#   sg vault-app fargate setup plan    [--cluster C] [--phase P] [--json]
#   sg vault-app fargate setup show    [--cluster C]
#
# Mutation gate: SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1
#   create/update/delete wrap with Mutation__Gate__Scope (sets all inner gates)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from typing import List

import typer
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                   import spec_cli_errors
from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Setup__Phase        import Enum__VAF__Setup__Phase
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Setup__Request  import Schema__VAF__Setup__Request
from sg_compute_specs.vault_app.fargate.service.Mutation__Gate__Scope        import Mutation__Gate__Scope
from sg_compute_specs.vault_app.fargate.service.Phase__Progress__Renderer    import Phase__Progress__Renderer
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Cluster__Resolver import Vault_App__Fargate__Cluster__Resolver
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Setup    import Vault_App__Fargate__Setup
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Reader import Vault_App__Fargate__Tags__Reader

_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='setup', help='Cluster-level provisioning (one-time setup).', no_args_is_help=True)


# ── phase-name map (CLI string → enum) ───────────────────────────────────────

_PHASE_MAP = {                                                                   # case-insensitive CLI name → enum
    'ecr'         : Enum__VAF__Setup__Phase.ECR,
    'iam'         : Enum__VAF__Setup__Phase.IAM,
    'logs'        : Enum__VAF__Setup__Phase.LOGS,
    'cluster'     : Enum__VAF__Setup__Phase.CLUSTER,
    'image-mirror': Enum__VAF__Setup__Phase.IMAGE_MIRROR,
    'task-def'    : Enum__VAF__Setup__Phase.TASK_DEF,
}


def _parse_phases(phase_strs: List[str]) -> list:                                # '' / ['all'] / ['ecr','iam'] → list[Enum] or None
    if not phase_strs:
        return None                                                               # None = all phases
    cleaned = [p.strip().lower() for p in phase_strs if p.strip()]
    if not cleaned or cleaned == ['all']:
        return None
    result = []
    for name in cleaned:
        enum_val = _PHASE_MAP.get(name)
        if enum_val is None:
            valid = ', '.join(_PHASE_MAP)
            raise typer.BadParameter(f'Unknown phase {name!r}; valid: {valid}')
        result.append(enum_val)
    return result or None


# ── factory helper ────────────────────────────────────────────────────────────

def _make_setup(ctx: typer.Context) -> Vault_App__Fargate__Setup:
    obj            = ctx.obj or {}
    fargate_client = obj.get('fargate_client')
    ecr_client     = obj.get('ecr_client')
    logs_client    = obj.get('logs_client')
    iam_client     = obj.get('iam_client')

    if fargate_client is None:
        from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client
        fargate_client = Fargate__AWS__Client()
    if ecr_client is None:
        from sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client import ECR__AWS__Client
        ecr_client = ECR__AWS__Client()
    if logs_client is None:
        from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client import Logs__AWS__Client
        logs_client = Logs__AWS__Client()
    if iam_client is None:
        from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client import IAM__AWS__Client
        iam_client = IAM__AWS__Client()

    return Vault_App__Fargate__Setup(
        ecr_client     = ecr_client,
        fargate_client = fargate_client,
        logs_client    = logs_client,
        iam_client     = iam_client,
    )


def _resolve_cluster(ctx: typer.Context, cluster_flag: str) -> str:
    obj            = ctx.obj or {}
    fargate_client = obj.get('fargate_client')
    if fargate_client is None:
        from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client
        fargate_client = Fargate__AWS__Client()
    return Vault_App__Fargate__Cluster__Resolver(
        fargate_client=fargate_client).resolve(cluster_flag)


def _build_request(cluster: str, phase_strs: List[str], **kwargs) -> Schema__VAF__Setup__Request:
    phases = _parse_phases(phase_strs)
    req    = Schema__VAF__Setup__Request(cluster_name=cluster, phases=phases)
    for k, v in kwargs.items():
        if v:
            setattr(req, k, v)
    return req


# ── report rendering ──────────────────────────────────────────────────────────

def _render_report_table(report, title: str) -> None:
    t = Table(title=title, box=None, show_header=True, padding=(0, 2))
    t.add_column('Phase',    style='bold')
    t.add_column('Status',   style='')
    t.add_column('ms',       justify='right', style='dim')
    t.add_column('Detail',   style='dim')
    for phase in (report.phases or []):
        status_str = str(phase.status) if phase.status else ''
        t.add_row(phase.name, status_str, str(phase.duration_ms), phase.detail)
    console.print()
    console.print(t)
    ok_label = '[green]ok[/green]' if report.ok else '[red]failed[/red]'
    console.print(f'\n  cluster: [bold]{report.cluster_name}[/]   '
                  f'total: {report.total_ms}ms   status: {ok_label}')
    console.print()


def _render_timings_table(report) -> None:
    t = Table(title='Phase timings', box=None, show_header=True, padding=(0, 2))
    t.add_column('Phase',   style='bold')
    t.add_column('ms',      justify='right', style='dim')
    t.add_column('Status',  style='')
    for phase in (report.phases or []):
        t.add_row(phase.name, str(phase.duration_ms), str(phase.status) if phase.status else '')
    console.print()
    console.print(t)


def _report_to_json(report) -> dict:
    return {
        'operation'   : report.operation,
        'cluster_name': report.cluster_name,
        'ok'          : report.ok,
        'total_ms'    : report.total_ms,
        'phases'      : [
            {
                'name'       : p.name,
                'status'     : str(p.status) if p.status else '',
                'duration_ms': p.duration_ms,
                'detail'     : p.detail,
            }
            for p in (report.phases or [])
        ],
    }


def _run_with_renderer(setup: Vault_App__Fargate__Setup, op: str,
                       request: Schema__VAF__Setup__Request,
                       as_json: bool):
    phase_names = [p.value for p in (request.phases or list(Enum__VAF__Setup__Phase))]
    if op == 'delete':
        phase_names = list(reversed(phase_names))

    if as_json:                                                                   # no live renderer in JSON mode
        return getattr(setup, op)(request)

    with Phase__Progress__Renderer(title=f'Setup — {op}', phases=phase_names) as renderer:
        setup.progress_cb = renderer.as_progress_cb()
        return getattr(setup, op)(request)


# ════════════════════════════════════════════════════════════════════════════════
# setup check
# ════════════════════════════════════════════════════════════════════════════════

@app.command('check')
@spec_cli_errors
def setup_check(ctx    : typer.Context,
                cluster: str       = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).'),
                phase  : List[str] = typer.Option([], '--phase',   help='Limit to phase(s): ecr|iam|logs|cluster|image-mirror|task-def|all.'),
                as_json: bool      = typer.Option(False, '--json', help='Machine-readable output.')):
    """Check which cluster resources already exist (read-only, no gate required)."""
    cluster_name = _resolve_cluster(ctx, cluster)
    request      = _build_request(cluster_name, list(phase))
    setup        = _make_setup(ctx)
    report       = setup.check(request)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return
    _render_report_table(report, title=f'Check — {cluster_name or "(auto)"}')


# ════════════════════════════════════════════════════════════════════════════════
# setup status
# ════════════════════════════════════════════════════════════════════════════════

@app.command('status')
@spec_cli_errors
def setup_status(ctx    : typer.Context,
                 cluster: str  = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).'),
                 as_json: bool = typer.Option(False, '--json',  help='Machine-readable output.')):
    """Show what is currently provisioned for this cluster (alias for check --all)."""
    cluster_name = _resolve_cluster(ctx, cluster)
    request      = _build_request(cluster_name, [])
    setup        = _make_setup(ctx)
    report       = setup.check(request)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return
    _render_report_table(report, title=f'Status — {cluster_name or "(auto)"}')


# ════════════════════════════════════════════════════════════════════════════════
# setup create
# ════════════════════════════════════════════════════════════════════════════════

@app.command('create')
@spec_cli_errors
def setup_create(ctx      : typer.Context,
                 cluster  : str       = typer.Option('', '--cluster',            help='Cluster name (auto-generated if omitted).'),
                 subnets  : str       = typer.Option('', '--subnets',            help='Comma-separated subnet IDs.'),
                 sg_id    : str       = typer.Option('', '--sg',                 help='Security group ID.'),
                 exec_role: str       = typer.Option('', '--execution-role-name', help='IAM execution role name.'),
                 log_group: str       = typer.Option('', '--log-group',           help='CloudWatch log group name.'),
                 src_image: str       = typer.Option('', '--source-image',        help='Docker image to mirror to ECR.'),
                 phase    : List[str] = typer.Option([], '--phase',              help='Limit to phase(s): ecr|iam|logs|cluster|image-mirror|task-def|all.'),
                 yes      : bool      = typer.Option(False, '--yes',             help='Skip confirmation prompt.'),
                 time_    : bool      = typer.Option(False, '--time',            help='Print phase timings table.'),
                 as_json  : bool      = typer.Option(False, '--json',            help='Machine-readable output.')):
    """Provision all cluster-level AWS resources (one-time setup)."""
    if os.environ.get(_GATE_ENV) != '1':
        console.print(Panel(
            f'[bold yellow]{_GATE_ENV}[/bold yellow] must be set to [bold]1[/bold] '
            f'to allow this mutation.\n\n'
            f'  [dim]export {_GATE_ENV}=1[/dim]',
            title='[red]Mutation gate[/red]',
            border_style='red',
        ))
        raise typer.Exit(1)

    cluster_name = cluster                                                        # empty = auto-generated by orchestrator
    request = _build_request(
        cluster_name, list(phase),
        subnets         = subnets,
        security_group  = sg_id,
        execution_role_name = exec_role,
        log_group       = log_group,
        source_image    = src_image,
    )

    if not yes and not as_json:
        typer.confirm(f'Provision cluster {cluster_name or "(auto)"}?', default=True, abort=True)

    with Mutation__Gate__Scope():
        report = _run_with_renderer(_make_setup(ctx), 'create', request, as_json)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return
    _render_report_table(report, title=f'Create — {report.cluster_name}')
    if time_:
        _render_timings_table(report)
    if not report.ok:
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# setup update
# ════════════════════════════════════════════════════════════════════════════════

@app.command('update')
@spec_cli_errors
def setup_update(ctx    : typer.Context,
                 cluster: str       = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).'),
                 phase  : List[str] = typer.Option([], '--phase',   help='Limit to phase(s): ecr|iam|logs|cluster|image-mirror|task-def|all.'),
                 yes    : bool      = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
                 time_  : bool      = typer.Option(False, '--time', help='Print phase timings table.'),
                 as_json: bool      = typer.Option(False, '--json', help='Machine-readable output.')):
    """Re-apply setup phases (e.g. after an image bump)."""
    if os.environ.get(_GATE_ENV) != '1':
        console.print(Panel(
            f'[bold yellow]{_GATE_ENV}[/bold yellow] must be set to [bold]1[/bold] '
            f'to allow this mutation.\n\n'
            f'  [dim]export {_GATE_ENV}=1[/dim]',
            title='[red]Mutation gate[/red]',
            border_style='red',
        ))
        raise typer.Exit(1)

    cluster_name = _resolve_cluster(ctx, cluster)
    request      = _build_request(cluster_name, list(phase))

    if not yes and not as_json:
        typer.confirm(f'Update cluster {cluster_name or "(auto)"}?', default=True, abort=True)

    with Mutation__Gate__Scope():
        report = _run_with_renderer(_make_setup(ctx), 'update', request, as_json)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return
    _render_report_table(report, title=f'Update — {report.cluster_name}')
    if time_:
        _render_timings_table(report)
    if not report.ok:
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# setup delete
# ════════════════════════════════════════════════════════════════════════════════

@app.command('delete')
@spec_cli_errors
def setup_delete(ctx    : typer.Context,
                 cluster: str       = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).'),
                 phase  : List[str] = typer.Option([], '--phase',   help='Limit to phase(s): ecr|iam|logs|cluster|image-mirror|task-def|all.'),
                 yes    : bool      = typer.Option(False, '--yes',  help='Skip confirmation prompt.'),
                 time_  : bool      = typer.Option(False, '--time', help='Print phase timings table.'),
                 as_json: bool      = typer.Option(False, '--json', help='Machine-readable output.')):
    """Tear down cluster-level AWS resources (phases run in reverse order)."""
    if os.environ.get(_GATE_ENV) != '1':
        console.print(Panel(
            f'[bold yellow]{_GATE_ENV}[/bold yellow] must be set to [bold]1[/bold] '
            f'to allow this mutation.\n\n'
            f'  [dim]export {_GATE_ENV}=1[/dim]',
            title='[red]Mutation gate[/red]',
            border_style='red',
        ))
        raise typer.Exit(1)

    cluster_name = _resolve_cluster(ctx, cluster)
    request      = _build_request(cluster_name, list(phase))

    if not yes and not as_json:
        typer.confirm(f'Delete cluster resources for {cluster_name or "(auto)"}?', default=False, abort=True)

    with Mutation__Gate__Scope():
        report = _run_with_renderer(_make_setup(ctx), 'delete', request, as_json)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return
    _render_report_table(report, title=f'Delete — {report.cluster_name}')
    if time_:
        _render_timings_table(report)
    if not report.ok:
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# setup plan
# ════════════════════════════════════════════════════════════════════════════════

@app.command('plan')
@spec_cli_errors
def setup_plan(ctx    : typer.Context,
               cluster: str       = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).'),
               phase  : List[str] = typer.Option([], '--phase',   help='Limit to phase(s): ecr|iam|logs|cluster|image-mirror|task-def|all.'),
               as_json: bool      = typer.Option(False, '--json', help='Machine-readable output.')):
    """Dry-run: show what would be created without making any changes."""
    cluster_name = _resolve_cluster(ctx, cluster)
    request      = _build_request(cluster_name, list(phase))
    setup        = _make_setup(ctx)
    report       = setup.check(request)                                          # check = read-only, shows what's missing

    if as_json:
        payload = _report_to_json(report)
        payload['operation'] = 'plan'
        typer.echo(json.dumps(payload, indent=2))
        return

    t = Table(title=f'Plan — {cluster_name or "(auto)"}', box=None,
              show_header=True, padding=(0, 2))
    t.add_column('Phase',   style='bold')
    t.add_column('State',   style='')
    t.add_column('Action',  style='cyan')
    t.add_column('Detail',  style='dim')
    for p in (report.phases or []):
        action = '[dim]skip (exists)[/dim]' if 'exists' in p.detail or 'active' in p.detail else '[cyan]create[/cyan]'
        t.add_row(p.name, str(p.status) if p.status else '', action, p.detail)
    console.print()
    console.print(t)
    console.print(f'\n  [dim]Dry-run — no changes made.[/]\n')


# ════════════════════════════════════════════════════════════════════════════════
# setup show
# ════════════════════════════════════════════════════════════════════════════════

@app.command('show')
@spec_cli_errors
def setup_show(ctx    : typer.Context,
               cluster: str = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).')):
    """Print the resolved cluster config (tags + active task definition)."""
    obj            = ctx.obj or {}
    fargate_client = obj.get('fargate_client')
    if fargate_client is None:
        from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client
        fargate_client = Fargate__AWS__Client()

    try:
        cluster_name = Vault_App__Fargate__Cluster__Resolver(
            fargate_client=fargate_client).resolve(cluster)
    except ValueError as exc:
        console.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)

    tags_reader = Vault_App__Fargate__Tags__Reader(fargate_client=fargate_client)
    config      = tags_reader.read(cluster_name)

    # ── cluster config table ──────────────────────────────────────────────────
    t1 = Table(title=f'Cluster config — {cluster_name}',
               box=None, show_header=False, padding=(0, 2))
    t1.add_column(style='bold', min_width=22)
    t1.add_column()
    for label, value in (
        ('cluster name',     config.cluster_name),
        ('subnets',          config.subnets          or '[dim](not set)[/dim]'),
        ('security group',   config.security_group    or '[dim](not set)[/dim]'),
        ('dns zone',         config.dns_zone          or '[dim](not set)[/dim]'),
        ('execution role',   config.execution_role_arn or '[dim](not set)[/dim]'),
        ('task role',        config.task_role_arn     or '[dim](not set)[/dim]'),
        ('log group',        config.log_group         or '[dim](not set)[/dim]'),
        ('ecr repo',         config.ecr_repo_name     or '[dim](not set)[/dim]'),
        ('region',           config.region            or '[dim](not set)[/dim]'),
        ('created at',       config.created_at        or '[dim](not set)[/dim]'),
    ):
        t1.add_row(label, value)
    console.print()
    console.print(t1)

    # ── active task definition table ──────────────────────────────────────────
    td = fargate_client.describe_task_definition(cluster_name)
    console.print()
    if td is None:
        console.print(f'  [dim]No task definition registered for family [bold]{cluster_name}[/bold][/dim]')
    else:
        t2 = Table(title=f'Active task definition — {cluster_name}',
                   box=None, show_header=False, padding=(0, 2))
        t2.add_column(style='bold', min_width=22)
        t2.add_column()
        t2.add_row('family',       td.family)
        t2.add_row('revision',     str(td.revision))
        t2.add_row('arn',          str(td.task_def_arn or ''))
        t2.add_row('status',       td.status or '')
        t2.add_row('cpu',          td.cpu or '—')
        t2.add_row('memory',       td.memory or '—')
        console.print(t2)
    console.print()
