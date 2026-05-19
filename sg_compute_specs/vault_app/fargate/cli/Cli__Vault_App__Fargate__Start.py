# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate/cli — Cli__Vault_App__Fargate__Start
# Typer CLI surface for task-level commands:
#   sg vault-app fargate start   [--slug] [--cluster] [--cpu] [--memory]
#                                [--launch-type] [--seed-vault-keys] [--access-token]
#                                [--no-public-ip] [--time] [--json] [--yes]
#   sg vault-app fargate stop    [--slug] [--cluster] [--yes] [--json]
#   sg vault-app fargate restart [--slug] [--cluster] [--json]
#   sg vault-app fargate health  [--slug] [--cluster] [--timeout]
#   sg vault-app fargate url     [--slug] [--cluster]
#   sg vault-app fargate open    [--slug] [--cluster]
#   sg vault-app fargate logs    [--slug] [--cluster] [--since] [--follow]
#   sg vault-app fargate list    [--cluster] [--clusters] [--json]
#   sg vault-app fargate info    [--slug] [--cluster]
#   sg vault-app fargate timings [--slug] [--cluster] [--last] [--json]
#
# Mutation gate: SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1 for start/stop/restart.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                            import spec_cli_errors
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Start__Request           import Schema__VAF__Start__Request
from sg_compute_specs.vault_app.fargate.service.Mutation__Gate__Scope                 import Mutation__Gate__Scope
from sg_compute_specs.vault_app.fargate.service.Phase__Progress__Renderer             import Phase__Progress__Renderer
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Cluster__Resolver import Vault_App__Fargate__Cluster__Resolver
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Health            import Vault_App__Fargate__Health
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Slug__Resolver    import Vault_App__Fargate__Slug__Resolver
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Starter           import Vault_App__Fargate__Starter
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Timings__Store    import Vault_App__Fargate__Timings__Store

_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'

console = Console()


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_fargate_client(ctx: typer.Context):
    obj = ctx.obj or {}
    client = obj.get('fargate_client')
    if client is None:
        from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client
        client = Fargate__AWS__Client()
    return client


def _get_logs_client(ctx: typer.Context):
    obj = ctx.obj or {}
    client = obj.get('logs_client')
    if client is None:
        from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client import Logs__AWS__Client
        client = Logs__AWS__Client()
    return client


def _get_ec2_client(ctx: typer.Context):
    obj    = ctx.obj or {}
    client = obj.get('ec2_client')
    if client is not None:
        return client
    try:
        from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client import EC2__AWS__Client
        return EC2__AWS__Client()
    except Exception:                                                              # noqa: BLE001 — ENI resolution is best-effort
        return None


def _resolve_cluster(fargate_client, cluster_flag: str) -> str:
    return Vault_App__Fargate__Cluster__Resolver(
        fargate_client=fargate_client).resolve(cluster_flag)


def _resolve_slug(fargate_client, cluster_name: str, slug_flag: str) -> str:
    return Vault_App__Fargate__Slug__Resolver(
        fargate_client=fargate_client).resolve(cluster_name, slug_flag)


def _resolve_task_arn(fargate_client, cluster_name: str, slug: str) -> str:     # find task_arn for a slug in the cluster
    tasks = fargate_client.list_tasks(cluster=cluster_name)
    for task in tasks:
        tags = task.tags or {}
        if isinstance(tags, list):                                                # handle raw [{key,value}] format
            tags = {t['key']: t['value'] for t in tags if 'key' in t}
        if tags.get('VaultApp__Slug') == slug:
            return str(task.task_arn)
    return ''


def _resolve_public_ip(task, ec2_client) -> tuple:                                # (public_ip, private_ip) via ENI; same pattern as Starter
    eni_id = str(getattr(task, 'eni_id', '') or '')
    if not eni_id or ec2_client is None:
        return '', ''
    eni = ec2_client.describe_network_interface(eni_id)
    if eni is None:
        return '', ''
    return str(eni.public_ip or ''), str(eni.private_ip or '')


def _gate_check():                                                                # print gate error and exit(1) if gate not set
    if os.environ.get(_GATE_ENV) != '1':
        console.print(Panel(
            f'[bold yellow]{_GATE_ENV}[/bold yellow] must be set to [bold]1[/bold] '
            f'to allow this mutation.\n\n'
            f'  [dim]export {_GATE_ENV}=1[/dim]',
            title='[red]Mutation gate[/red]',
            border_style='red',
        ))
        raise typer.Exit(1)


def _get_starter(ctx: typer.Context) -> Vault_App__Fargate__Starter:
    obj            = ctx.obj or {}
    fargate_client = _get_fargate_client(ctx)
    ec2_client     = _get_ec2_client(ctx)
    health         = obj.get('health')                                            # injectable for tests
    timings_store  = obj.get('timings_store')                                     # injectable for tests
    return Vault_App__Fargate__Starter(
        fargate_client = fargate_client,
        ec2_client     = ec2_client,
        health         = health,
        timings_store  = timings_store,
    )


# ── report rendering ──────────────────────────────────────────────────────────

def _render_start_panel(report) -> None:
    lines = []
    lines.append(f'slug          : {report.slug}')
    lines.append(f'cluster       : {report.cluster_name}')
    lines.append(f'task arn      : {report.task_arn}')
    lines.append(f'public ip     : {report.public_ip or "(none)"}')
    lines.append(f'vault url     : {report.vault_url}')
    if report.access_token:
        lines.append(f'access token  : {report.access_token}  (shown ONCE)')
    lines.append(f'task ready    : {report.task_ready_ms / 1000:.1f} s')
    lines.append(f'vault ready   : {report.vault_ready_ms / 1000:.1f} s')
    lines.append(f'total         : {report.total_ms / 1000:.1f} s')
    console.print()
    console.print(Panel('\n'.join(lines), title='[bold]vault-app on Fargate[/bold]'))
    console.print()


def _render_timings_table(report, title: str = 'Phase timings') -> None:
    t = Table(title=title, box=None, show_header=True, padding=(0, 2))
    t.add_column('Phase',   style='bold')
    t.add_column('ms',      justify='right', style='dim')
    t.add_column('Status',  style='')
    for phase in (report.phases or []):
        t.add_row(phase.name, str(phase.duration_ms), str(phase.status) if phase.status else '')
    console.print()
    console.print(t)


def _report_to_json(report) -> dict:
    return {
        'slug'           : report.slug,
        'cluster_name'   : report.cluster_name,
        'task_arn'       : report.task_arn,
        'task_definition': report.task_definition,
        'public_ip'      : report.public_ip,
        'private_ip'     : report.private_ip,
        'vault_url'      : report.vault_url,
        'access_token'   : report.access_token,
        'ok'             : report.ok,
        'error'          : report.error,
        'phases'         : [
            {
                'name'       : p.name,
                'status'     : str(p.status) if p.status else '',
                'duration_ms': p.duration_ms,
                'detail'     : p.detail,
            }
            for p in (report.phases or [])
        ],
        'timings'        : {
            'task_ready_ms' : report.task_ready_ms,
            'vault_ready_ms': report.vault_ready_ms,
            'total_ms'      : report.total_ms,
        },
        'executed_at'    : report.executed_at,
    }


# ════════════════════════════════════════════════════════════════════════════════
# start
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_start(ctx          : typer.Context,
                  slug         : str  = typer.Option('',        '--slug',            help='Task slug (auto-generated if omitted).'),
                  cluster      : str  = typer.Option('',        '--cluster',         help='Cluster name (auto-resolved if omitted).'),
                  cpu          : str  = typer.Option('',        '--cpu',             help='CPU units (e.g. 512).'),
                  memory       : str  = typer.Option('',        '--memory',          help='Memory in MiB (e.g. 1024).'),
                  launch_type  : str  = typer.Option('FARGATE', '--launch-type',     help='FARGATE or FARGATE_SPOT.'),
                  seed_vault_keys: str = typer.Option('',       '--seed-vault-keys', help='Comma-separated vault keys to seed.'),
                  access_token : str  = typer.Option('',        '--access-token',    help='Vault access token.'),
                  tls          : bool = typer.Option(False,     '--tls/--no-tls',    help='Enable TLS (port 443); omit for direct-IP HTTP (port 8080, default).'),
                  public_ip    : bool = typer.Option(True,      '--public-ip/--no-public-ip', help='Assign public IP.'),
                  time_        : bool = typer.Option(False,     '--time',            help='Print phase timings table.'),
                  as_json      : bool = typer.Option(False,     '--json',            help='Machine-readable output.'),
                  yes          : bool = typer.Option(False,     '--yes',             help='Skip confirmation prompt.')):
    """Start a vault-app container on Fargate (fast-path orchestrator)."""
    _gate_check()

    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)

    if not yes and not as_json:
        typer.confirm(f'Start vault on cluster {cluster_name or "(auto)"}?', default=True, abort=True)

    request = Schema__VAF__Start__Request(
        cluster_name    = cluster_name,
        slug            = slug,
        access_token    = access_token,
        seed_vault_keys = seed_vault_keys,
        with_tls        = tls,
        public_ip       = public_ip,
        launch_type     = launch_type,
        cpu             = cpu,
        memory          = memory,
    )

    starter = _get_starter(ctx)

    with Mutation__Gate__Scope():
        if as_json:
            report = starter.start(request)
        else:
            phase_names = ['resolve-config', 'run-task', 'wait-running',
                           'resolve-eni', 'wait-health']
            with Phase__Progress__Renderer(title='Start — vault-app', phases=phase_names) as renderer:
                starter.progress_cb = renderer.as_progress_cb()
                report = starter.start(request)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return

    _render_start_panel(report)
    if time_:
        _render_timings_table(report)

    if not report.ok:
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# stop
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_stop(ctx    : typer.Context,
                 slug   : str  = typer.Option('',    '--slug',    help='Task slug (auto-resolved if one running task).'),
                 cluster: str  = typer.Option('',    '--cluster', help='Cluster name (auto-resolved if omitted).'),
                 yes    : bool = typer.Option(False,  '--yes',     help='Skip confirmation prompt.'),
                 as_json: bool = typer.Option(False,  '--json',    help='Machine-readable output.')):
    """Stop a running vault-app container."""
    _gate_check()

    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)
    slug_name      = _resolve_slug(fargate_client, cluster_name, slug)
    task_arn       = _resolve_task_arn(fargate_client, cluster_name, slug_name)

    if not task_arn:
        console.print(f'  [red]✗[/]  No task ARN found for slug [bold]{slug_name}[/] in cluster [bold]{cluster_name}[/]')
        raise typer.Exit(1)

    if not yes and not as_json:
        typer.confirm(f'Stop vault {slug_name!r} in cluster {cluster_name!r}?', default=False, abort=True)

    with Mutation__Gate__Scope():
        fargate_client.stop_task(task_arn, cluster=cluster_name)

    if as_json:
        typer.echo(json.dumps({'slug': slug_name, 'task_arn': task_arn, 'stopped': True}, indent=2))
        return

    console.print(f'[green]Stopped[/green] {slug_name}')


# ════════════════════════════════════════════════════════════════════════════════
# restart
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_restart(ctx    : typer.Context,
                    slug   : str  = typer.Option('',    '--slug',    help='Task slug (required if previous task already stopped).'),
                    cluster: str  = typer.Option('',    '--cluster', help='Cluster name (auto-resolved if omitted).'),
                    as_json: bool = typer.Option(False,  '--json',    help='Machine-readable output.')):
    """Stop then re-start a vault-app container (keeps same slug + cluster)."""
    _gate_check()

    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)

    # Try to resolve slug from a running task; if none exists, fall back to --slug.
    slug_name = slug
    task_arn  = ''
    try:
        slug_name = _resolve_slug(fargate_client, cluster_name, slug)
        task_arn  = _resolve_task_arn(fargate_client, cluster_name, slug_name)
    except ValueError:
        if not slug:                                                              # no running task and no explicit slug → can't restart
            console.print('  [red]✗[/]  No running task to restart; pass --slug to start a fresh task.')
            raise typer.Exit(1)

    # ── stop ─────────────────────────────────────────────────────────────────
    with Mutation__Gate__Scope():
        if task_arn:
            fargate_client.stop_task(task_arn, cluster=cluster_name)

    # ── start ─────────────────────────────────────────────────────────────────
    request = Schema__VAF__Start__Request(
        cluster_name = cluster_name,
        slug         = slug_name,
    )
    starter = _get_starter(ctx)

    with Mutation__Gate__Scope():
        report = starter.start(request)

    if as_json:
        typer.echo(json.dumps(_report_to_json(report), indent=2))
        return

    _render_start_panel(report)
    if not report.ok:
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# health
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_health(ctx    : typer.Context,
                   slug   : str = typer.Option('', '--slug',    help='Task slug (auto-resolved if one running task).'),
                   cluster: str = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).'),
                   timeout: int = typer.Option(30, '--timeout', help='Max seconds to wait for healthy response.')):
    """Check vault health; polls until healthy or timeout."""
    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)
    slug_name      = _resolve_slug(fargate_client, cluster_name, slug)
    task_arn       = _resolve_task_arn(fargate_client, cluster_name, slug_name)

    if not task_arn:
        console.print(f'  [red]✗[/]  No running task for slug [bold]{slug_name}[/]')
        raise typer.Exit(1)

    task = fargate_client.describe_task(task_arn, cluster=cluster_name)
    if task is None:
        console.print(f'  [red]✗[/]  Task not found: {task_arn}')
        raise typer.Exit(1)

    obj                    = ctx.obj or {}
    health                 = obj.get('health') or Vault_App__Fargate__Health(timeout_seconds=timeout)
    ec2_client             = _get_ec2_client(ctx)
    public_ip, private_ip  = _resolve_public_ip(task, ec2_client)
    host                   = public_ip or private_ip

    if not host:
        console.print(f'  [red]✗[/]  No IP resolved for task [bold]{task_arn}[/] '
                      f'(eni_id={task.eni_id or "(none)"})')
        raise typer.Exit(1)

    vault_url     = f'https://{host}:443'
    result        = health.wait_for(vault_url + '/info/health')

    if result.ok:
        console.print(f'[green]healthy[/green]  ({result.attempts} attempt(s), {result.duration_ms}ms)')
    else:
        console.print(f'[red]unhealthy[/red] (last error: {result.last_error}, attempts: {result.attempts})')
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# url
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_url(ctx    : typer.Context,
                slug   : str = typer.Option('', '--slug',    help='Task slug (auto-resolved if one running task).'),
                cluster: str = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).')):
    """Print the vault URL (plain text, easy to pipe)."""
    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)
    slug_name      = _resolve_slug(fargate_client, cluster_name, slug)
    task_arn       = _resolve_task_arn(fargate_client, cluster_name, slug_name)

    if not task_arn:
        console.print(f'  [red]✗[/]  No running task for slug [bold]{slug_name}[/]')
        raise typer.Exit(1)

    task = fargate_client.describe_task(task_arn, cluster=cluster_name)
    if task is None:
        console.print(f'  [red]✗[/]  Task not found: {task_arn}')
        raise typer.Exit(1)

    ec2_client            = _get_ec2_client(ctx)
    public_ip, private_ip = _resolve_public_ip(task, ec2_client)
    host                  = public_ip or private_ip
    if not host:
        console.print('  [red]✗[/]  No IP available for task '
                      f'(eni_id={task.eni_id or "(none)"}).')
        raise typer.Exit(1)

    vault_url = f'https://{host}:443'
    typer.echo(vault_url)


# ════════════════════════════════════════════════════════════════════════════════
# open
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_open(ctx    : typer.Context,
                 slug   : str = typer.Option('', '--slug',    help='Task slug (auto-resolved if one running task).'),
                 cluster: str = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).')):
    """Resolve vault URL and open it in the default browser."""
    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)
    slug_name      = _resolve_slug(fargate_client, cluster_name, slug)
    task_arn       = _resolve_task_arn(fargate_client, cluster_name, slug_name)

    if not task_arn:
        console.print(f'  [red]✗[/]  No running task for slug [bold]{slug_name}[/]')
        raise typer.Exit(1)

    task = fargate_client.describe_task(task_arn, cluster=cluster_name)
    if task is None:
        console.print(f'  [red]✗[/]  Task not found: {task_arn}')
        raise typer.Exit(1)

    ec2_client            = _get_ec2_client(ctx)
    public_ip, private_ip = _resolve_public_ip(task, ec2_client)
    host                  = public_ip or private_ip
    if not host:
        console.print('  [red]✗[/]  No IP available for task '
                      f'(eni_id={task.eni_id or "(none)"}).')
        raise typer.Exit(1)

    vault_url = f'https://{host}:443'
    typer.launch(vault_url)


# ════════════════════════════════════════════════════════════════════════════════
# logs
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_logs(ctx    : typer.Context,
                 slug   : str  = typer.Option('',    '--slug',    help='Task slug (auto-resolved if one running task).'),
                 cluster: str  = typer.Option('',    '--cluster', help='Cluster name (auto-resolved if omitted).'),
                 since  : int  = typer.Option(30,    '--since',   help='Look back N minutes (default 30).'),
                 follow : bool = typer.Option(False,  '--follow',  help='Poll for new events (Ctrl-C to stop).')):
    """Stream CloudWatch log events for a running vault task."""
    fargate_client = _get_fargate_client(ctx)
    logs_client    = _get_logs_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)
    slug_name      = _resolve_slug(fargate_client, cluster_name, slug)

    # ── resolve log group from cluster tags ───────────────────────────────────
    from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Reader import Vault_App__Fargate__Tags__Reader
    config    = Vault_App__Fargate__Tags__Reader(fargate_client=fargate_client).read(cluster_name)
    log_group = config.log_group or '/ecs/vault-app'

    events = logs_client.tail_log_group(
        name           = log_group,
        stream_prefix  = slug_name,
        since_minutes  = since,
        follow         = follow,
    )

    if not events:
        console.print(f'[dim]No log events found in {log_group}[/dim]')
        return

    for ev in events:
        stream  = ev.get('stream', '')
        message = ev.get('message', '')
        typer.echo(f'[{stream}] {message}')


# ════════════════════════════════════════════════════════════════════════════════
# list
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_list(ctx         : typer.Context,
                 cluster     : str  = typer.Option('',    '--cluster',  help='Limit to this cluster.'),
                 list_clusters: bool = typer.Option(False, '--clusters', help='List clusters themselves (no tasks).'),
                 as_json     : bool = typer.Option(False,  '--json',     help='Machine-readable output.')):
    """List vault tasks (or clusters with --clusters)."""
    fargate_client = _get_fargate_client(ctx)

    if list_clusters:                                                              # ── list clusters ────────────────────
        clusters = fargate_client.list_clusters()
        if as_json:
            typer.echo(json.dumps([
                {'cluster_name': str(c.cluster_name), 'status': c.status,
                 'running_tasks': c.running_tasks}
                for c in clusters
            ], indent=2))
            return
        if not clusters:
            console.print('No ECS clusters found.')
            return
        tbl = Table(title='Vault-App Clusters')
        tbl.add_column('Name',    style='cyan')
        tbl.add_column('Status',  style='green')
        tbl.add_column('Running', justify='right')
        for c in clusters:
            tbl.add_row(str(c.cluster_name), c.status, str(c.running_tasks))
        console.print(tbl)
        return

    # ── list tasks ────────────────────────────────────────────────────────────
    tasks = fargate_client.list_tasks(cluster=cluster)
    if as_json:
        rows = []
        for task in tasks:
            tags = task.tags or {}
            if isinstance(tags, list):
                tags = {t['key']: t['value'] for t in tags if 'key' in t}
            rows.append({
                'slug'       : tags.get('VaultApp__Slug', ''),
                'task_arn'   : str(task.task_arn),
                'cluster'    : str(task.cluster_name),
                'status'     : str(task.status),
                'started_at' : task.started_at or '',
            })
        typer.echo(json.dumps(rows, indent=2))
        return

    if not tasks:
        console.print('No running tasks found.')
        return

    tbl = Table(title='Vault Tasks')
    tbl.add_column('Slug',       style='cyan')
    tbl.add_column('Cluster',    style='green')
    tbl.add_column('Status')
    tbl.add_column('Task ARN',   style='dim')
    tbl.add_column('Started')
    for task in tasks:
        tags = task.tags or {}
        if isinstance(tags, list):
            tags = {t['key']: t['value'] for t in tags if 'key' in t}
        slug_label  = tags.get('VaultApp__Slug', '—')
        short_arn   = str(task.task_arn).split('/')[-1] if '/' in str(task.task_arn) else str(task.task_arn)
        tbl.add_row(
            slug_label,
            str(task.cluster_name),
            str(task.status),
            short_arn,
            (task.started_at or '—')[:19],
        )
    console.print(tbl)


# ════════════════════════════════════════════════════════════════════════════════
# info
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_info(ctx    : typer.Context,
                 slug   : str = typer.Option('', '--slug',    help='Task slug (auto-resolved if one running task).'),
                 cluster: str = typer.Option('', '--cluster', help='Cluster name (auto-resolved if omitted).')):
    """Show rich task details + last 3 timings from the timings store."""
    fargate_client = _get_fargate_client(ctx)
    cluster_name   = _resolve_cluster(fargate_client, cluster)
    slug_name      = _resolve_slug(fargate_client, cluster_name, slug)
    task_arn       = _resolve_task_arn(fargate_client, cluster_name, slug_name)

    if not task_arn:
        console.print(f'  [red]✗[/]  No running task for slug [bold]{slug_name}[/]')
        raise typer.Exit(1)

    task = fargate_client.describe_task(task_arn, cluster=cluster_name)
    if task is None:
        console.print(f'  [red]✗[/]  Task not found: {task_arn}')
        raise typer.Exit(1)

    # ── task fields ───────────────────────────────────────────────────────────
    t1 = Table(title=f'Task info — {slug_name}', box=None, show_header=False, padding=(0, 2))
    t1.add_column(style='bold', min_width=16)
    t1.add_column()
    t1.add_row('slug',       slug_name)
    t1.add_row('cluster',    str(task.cluster_name))
    t1.add_row('task arn',   str(task.task_arn))
    t1.add_row('task def',   str(task.task_definition))
    t1.add_row('status',     str(task.status))
    t1.add_row('started at', task.started_at or '—')
    t1.add_row('stopped at', task.stopped_at  or '—')
    t1.add_row('stop reason',task.stopped_reason or '—')
    console.print()
    console.print(t1)

    # ── last 3 timings ────────────────────────────────────────────────────────
    obj           = ctx.obj or {}
    timings_store = obj.get('timings_store') or Vault_App__Fargate__Timings__Store()
    records       = timings_store.last(3)
    slug_records  = [r for r in records if r.slug == slug_name]

    if slug_records:
        t2 = Table(title='Recent timings', box=None, show_header=True, padding=(0, 2))
        t2.add_column('When',        style='dim')
        t2.add_column('task_ready',  justify='right', style='dim')
        t2.add_column('vault_ready', justify='right', style='dim')
        t2.add_column('total',       justify='right', style='dim')
        for r in slug_records:
            t2.add_row(r.executed_at[:19] if r.executed_at else '—',
                       f'{r.task_ready_ms}ms',
                       f'{r.vault_ready_ms}ms',
                       f'{r.total_ms}ms')
        console.print()
        console.print(t2)
    else:
        console.print(f'\n  [dim]No timing records for slug {slug_name!r}.[/dim]')

    console.print()


# ════════════════════════════════════════════════════════════════════════════════
# timings
# ════════════════════════════════════════════════════════════════════════════════

@spec_cli_errors
def fargate_timings(ctx    : typer.Context,
                    slug   : str  = typer.Option('',    '--slug',    help='Filter by slug (optional).'),
                    cluster: str  = typer.Option('',    '--cluster', help='Filter by cluster (optional).'),
                    last   : int  = typer.Option(10,    '--last',    help='Number of most recent records to show.'),
                    as_json: bool = typer.Option(False,  '--json',    help='Machine-readable output.')):
    """Show historical start timings from the local timings store."""
    obj           = ctx.obj or {}
    timings_store = obj.get('timings_store') or Vault_App__Fargate__Timings__Store()
    records       = timings_store.last(last)

    if slug:                                                                      # optional slug filter
        records = [r for r in records if r.slug == slug]
    if cluster:                                                                   # optional cluster filter
        records = [r for r in records if r.cluster_name == cluster]

    if as_json:
        typer.echo(json.dumps([
            {
                'slug'           : r.slug,
                'cluster_name'   : r.cluster_name,
                'task_ready_ms'  : r.task_ready_ms,
                'vault_ready_ms' : r.vault_ready_ms,
                'total_ms'       : r.total_ms,
                'launch_type'    : r.launch_type,
                'executed_at'    : r.executed_at,
            }
            for r in records
        ], indent=2))
        return

    if not records:
        console.print('[dim]No timing records found.[/dim]')
        return

    tbl = Table(title=f'Start timings (last {last})', box=None,
                show_header=True, padding=(0, 2))
    tbl.add_column('When',        style='dim')
    tbl.add_column('Slug',        style='cyan')
    tbl.add_column('Cluster',     style='green')
    tbl.add_column('task_ready',  justify='right', style='dim')
    tbl.add_column('vault_ready', justify='right', style='dim')
    tbl.add_column('total',       justify='right', style='dim')
    for r in records:
        tbl.add_row(
            r.executed_at[:19] if r.executed_at else '—',
            r.slug,
            r.cluster_name,
            f'{r.task_ready_ms}ms',
            f'{r.vault_ready_ms}ms',
            f'{r.total_ms}ms',
        )
    console.print()
    console.print(tbl)
    console.print()
