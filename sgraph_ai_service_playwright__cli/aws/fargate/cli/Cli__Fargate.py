# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Fargate
# Typer CLI surface for ECS Fargate cluster, task-def, and task management.
#
# Command tree:
#   sg aws fargate cluster list            [--json]
#   sg aws fargate cluster describe <name> [--json]
#   sg aws fargate cluster create  <name>  [--tag k=v] [--yes]
#   sg aws fargate cluster delete  <name>  [--yes]
#   sg aws fargate task-def list           [--family F] [--json]
#   sg aws fargate task-def show   <fam:rev> [--json]
#   sg aws fargate task-def register --name NAME --image IMG [--cpu 256]
#                                    [--memory 512] [--env k=v] [--yes]
#   sg aws fargate task list               [--cluster C] [--family F] [--json]
#   sg aws fargate task describe <arn>     [--cluster C] [--json]
#   sg aws fargate task run   --cluster C --task-def F:R [--count 1]
#                              [--subnet S] [--sg G] [--yes]
#   sg aws fargate task stop  <arn>        [--cluster C] [--reason R] [--yes]
#   sg aws fargate task logs  <arn>        [--cluster C] [--since 30m] [--json]
#
# Read-only commands always allowed.
# Mutations require SG_AWS__FARGATE__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time
from typing import List, Optional

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate              import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client

console = Console()

_MUTATION_ENV = 'SG_AWS__FARGATE__ALLOW_MUTATIONS'

app         = typer.Typer(name='fargate',  help='ECS Fargate cluster and task management.', no_args_is_help=True)
cluster_app = typer.Typer(name='cluster',  help='ECS cluster lifecycle.',                   no_args_is_help=True)
task_def_app= typer.Typer(name='task-def', help='ECS task definition management.',          no_args_is_help=True)
task_app    = typer.Typer(name='task',     help='ECS task run/stop/logs.',                  no_args_is_help=True)

app.add_typer(cluster_app,  name='cluster' )
app.add_typer(task_def_app, name='task-def')
app.add_typer(task_app,     name='task'    )


def _client() -> Fargate__AWS__Client:                                            # seam for in-memory test injection
    return Fargate__AWS__Client()


# ════════════════════════════════════════════════════════════════════════════════
# cluster list
# ════════════════════════════════════════════════════════════════════════════════

@cluster_app.command('list')
def cluster_list(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List all ECS Fargate clusters in the account/region."""
    clusters = _client().list_clusters()
    if as_json:
        typer.echo(json.dumps([dict(
            cluster_name  = str(c.cluster_name),
            cluster_arn   = c.cluster_arn,
            status        = c.status,
            running_tasks = c.running_tasks,
            pending_tasks = c.pending_tasks,
            active_services=c.active_services,
        ) for c in clusters], indent=2))
        return
    if not clusters:
        console.print('No ECS clusters found.')
        return
    t = Table(title='ECS Clusters')
    t.add_column('Name',     style='cyan')
    t.add_column('Status',   style='green')
    t.add_column('Running',  justify='right')
    t.add_column('Pending',  justify='right')
    t.add_column('Services', justify='right')
    for c in clusters:
        t.add_row(str(c.cluster_name), c.status,
                  str(c.running_tasks), str(c.pending_tasks), str(c.active_services))
    console.print(t)


# ════════════════════════════════════════════════════════════════════════════════
# cluster describe
# ════════════════════════════════════════════════════════════════════════════════

@cluster_app.command('describe')
def cluster_describe(name   : str  = typer.Argument(...,   help='Cluster name.'),
                     as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show details for an ECS cluster."""
    c = _client().describe_cluster(name)
    if c is None:
        console.print(f'[red]Cluster not found:[/red] {name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            cluster_name   = str(c.cluster_name),
            cluster_arn    = c.cluster_arn,
            status         = c.status,
            running_tasks  = c.running_tasks,
            pending_tasks  = c.pending_tasks,
            active_services= c.active_services,
        ), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18)
    t.add_column()
    t.add_row('name',            str(c.cluster_name))
    t.add_row('arn',             c.cluster_arn)
    t.add_row('status',          c.status)
    t.add_row('running tasks',   str(c.running_tasks))
    t.add_row('pending tasks',   str(c.pending_tasks))
    t.add_row('active services', str(c.active_services))
    console.print()
    console.print(t)
    console.print()


# ════════════════════════════════════════════════════════════════════════════════
# cluster create
# ════════════════════════════════════════════════════════════════════════════════

@cluster_app.command('create')
@require_mutation_gate(_MUTATION_ENV)
def cluster_create(name   : str        = typer.Argument(...,   help='Cluster name.'),
                   tag    : List[str]  = typer.Option([],  '--tag',  '-t',
                                                     help='Tag as k=v (repeatable).'),
                   yes    : bool       = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
                   as_json: bool       = typer.Option(False, '--json', help='Output as JSON.')):
    """Create an ECS Fargate cluster with FARGATE + FARGATE_SPOT capacity providers."""
    if not yes:
        typer.confirm(f'Create cluster "{name}"?', abort=True)
    tags = {}
    for t in tag:
        k, _, v = t.partition('=')
        if k:
            tags[k] = v
    c = _client().create_cluster(name, tags=tags)
    if as_json:
        typer.echo(json.dumps(dict(cluster_name=str(c.cluster_name),
                                   cluster_arn =c.cluster_arn,
                                   status      =c.status), indent=2))
        return
    console.print(f'[green]Created[/green] {name}  ({c.cluster_arn})')


# ════════════════════════════════════════════════════════════════════════════════
# cluster delete
# ════════════════════════════════════════════════════════════════════════════════

@cluster_app.command('delete')
@require_mutation_gate(_MUTATION_ENV)
def cluster_delete(name: str  = typer.Argument(...,   help='Cluster name.'),
                   yes : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.')):
    """Delete an ECS cluster (refuses if tasks are still running)."""
    if not yes:
        typer.confirm(f'Delete cluster "{name}"?', abort=True)
    try:
        ok = _client().delete_cluster(name)
    except ValueError as exc:
        console.print(f'[red]Cannot delete:[/red] {exc}')
        raise typer.Exit(1)
    if ok:
        console.print(f'[green]Deleted[/green] {name}')
    else:
        console.print(f'[red]Failed to delete[/red] {name}')
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# task-def list
# ════════════════════════════════════════════════════════════════════════════════

@task_def_app.command('list')
def task_def_list(family : str  = typer.Option('',    '--family', '-f', help='Filter by family prefix.'),
                  as_json: bool = typer.Option(False, '--json',          help='Output as JSON.')):
    """List active ECS task definitions."""
    tds = _client().list_task_definitions(family=family)
    if as_json:
        typer.echo(json.dumps([dict(
            family         = td.family,
            revision       = td.revision,
            family_revision= str(td.family_revision),
            status         = td.status,
            cpu            = td.cpu,
            memory         = td.memory,
        ) for td in tds], indent=2))
        return
    if not tds:
        console.print('No task definitions found.')
        return
    t = Table(title='ECS Task Definitions')
    t.add_column('Family:Rev', style='cyan')
    t.add_column('Status',     style='green')
    t.add_column('CPU',        justify='right')
    t.add_column('Memory',     justify='right')
    for td in tds:
        t.add_row(str(td.family_revision), td.status, td.cpu or '—', td.memory or '—')
    console.print(t)


# ════════════════════════════════════════════════════════════════════════════════
# task-def show
# ════════════════════════════════════════════════════════════════════════════════

@task_def_app.command('show')
def task_def_show(family_rev: str  = typer.Argument(...,   help='Family:revision, e.g. my-task:3.'),
                  as_json   : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show details of a task definition."""
    td = _client().describe_task_definition(family_rev)
    if td is None:
        console.print(f'[red]Task definition not found:[/red] {family_rev}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            family         = td.family,
            revision       = td.revision,
            task_def_arn   = td.task_def_arn,
            status         = td.status,
            cpu            = td.cpu,
            memory         = td.memory,
            launch_type    = str(td.launch_type),
        ), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=14)
    t.add_column()
    t.add_row('family',   td.family)
    t.add_row('revision', str(td.revision))
    t.add_row('arn',      td.task_def_arn)
    t.add_row('status',   td.status)
    t.add_row('cpu',      td.cpu or '—')
    t.add_row('memory',   td.memory or '—')
    console.print()
    console.print(t)
    console.print()


# ════════════════════════════════════════════════════════════════════════════════
# task-def register
# ════════════════════════════════════════════════════════════════════════════════

@task_def_app.command('register')
@require_mutation_gate(_MUTATION_ENV)
def task_def_register(name   : str       = typer.Option(..., '--name',   '-n', help='Task family name.'),
                      image  : str       = typer.Option(..., '--image',  '-i', help='Container image URI.'),
                      cpu    : str       = typer.Option('256',  '--cpu',  help='vCPU units (e.g. 256, 512).'),
                      memory : str       = typer.Option('512',  '--memory', help='Memory in MiB (e.g. 512, 1024).'),
                      env    : List[str] = typer.Option([],     '--env',  '-e',
                                                        help='Env var as K=V (repeatable).'),
                      yes    : bool      = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
                      as_json: bool      = typer.Option(False, '--json', help='Output as JSON.')):
    """Register a new ECS task definition revision."""
    if not yes:
        typer.confirm(f'Register task definition "{name}" with image "{image}"?', abort=True)
    env_dict = {}
    for e in env:
        k, _, v = e.partition('=')
        if k:
            env_dict[k] = v
    td = _client().register_task_definition(name=name, image=image,
                                             cpu=cpu, memory=memory, env=env_dict)
    if td is None:
        console.print('[red]Failed to register task definition.[/red]')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            family         = td.family,
            revision       = td.revision,
            task_def_arn   = td.task_def_arn,
        ), indent=2))
        return
    console.print(f'[green]Registered[/green] {td.family}:{td.revision}')
    console.print(f'  ARN: {td.task_def_arn}')


# ════════════════════════════════════════════════════════════════════════════════
# task list
# ════════════════════════════════════════════════════════════════════════════════

@task_app.command('list')
def task_list(cluster: str  = typer.Option('',    '--cluster', '-c', help='Filter by cluster name.'),
              family : str  = typer.Option('',    '--family',  '-f', help='Filter by task family.'),
              as_json: bool = typer.Option(False, '--json',          help='Output as JSON.')):
    """List running ECS tasks."""
    tasks = _client().list_tasks(cluster=cluster, family=family)
    if as_json:
        typer.echo(json.dumps([dict(
            task_arn       = str(t.task_arn),
            cluster_name   = str(t.cluster_name),
            task_definition= str(t.task_definition),
            status         = str(t.status),
            started_at     = t.started_at,
        ) for t in tasks], indent=2))
        return
    if not tasks:
        console.print('No running tasks found.')
        return
    tbl = Table(title='ECS Tasks')
    tbl.add_column('Task ARN',   style='cyan')
    tbl.add_column('Cluster',    style='green')
    tbl.add_column('Task Def',   style='dim')
    tbl.add_column('Status')
    tbl.add_column('Started')
    for t in tasks:
        short_arn = str(t.task_arn).split('/')[-1] if '/' in str(t.task_arn) else str(t.task_arn)
        tbl.add_row(short_arn, str(t.cluster_name), str(t.task_definition),
                    str(t.status), t.started_at[:19] if t.started_at else '—')
    console.print(tbl)


# ════════════════════════════════════════════════════════════════════════════════
# task describe
# ════════════════════════════════════════════════════════════════════════════════

@task_app.command('describe')
def task_describe(task_arn: str  = typer.Argument(...,   help='Task ARN.'),
                  cluster : str  = typer.Option('',    '--cluster', '-c', help='Cluster name.'),
                  as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show details for a running or stopped ECS task."""
    t = _client().describe_task(task_arn, cluster=cluster)
    if t is None:
        console.print(f'[red]Task not found:[/red] {task_arn}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            task_arn        = str(t.task_arn),
            cluster_name    = str(t.cluster_name),
            task_definition = str(t.task_definition),
            status          = str(t.status),
            last_status     = t.last_status,
            desired_status  = t.desired_status,
            started_at      = t.started_at,
            stopped_at      = t.stopped_at,
            stopped_reason  = t.stopped_reason,
            group           = t.group,
        ), indent=2))
        return
    tbl = Table(box=None, show_header=False, padding=(0, 2))
    tbl.add_column(style='bold', min_width=16)
    tbl.add_column()
    tbl.add_row('task arn',      str(t.task_arn))
    tbl.add_row('cluster',       str(t.cluster_name))
    tbl.add_row('task def',      str(t.task_definition))
    tbl.add_row('status',        str(t.status))
    tbl.add_row('started at',    t.started_at or '—')
    tbl.add_row('stopped at',    t.stopped_at  or '—')
    tbl.add_row('stop reason',   t.stopped_reason or '—')
    tbl.add_row('group',         t.group or '—')
    console.print()
    console.print(tbl)
    console.print()


# ════════════════════════════════════════════════════════════════════════════════
# task run
# ════════════════════════════════════════════════════════════════════════════════

@task_app.command('run')
@require_mutation_gate(_MUTATION_ENV)
def task_run(cluster         : str       = typer.Option(...,  '--cluster',  '-c', help='Target cluster name.'),
             task_def        : str       = typer.Option(...,  '--task-def', '-t', help='Task definition family:revision.'),
             count           : int       = typer.Option(1,    '--count',          help='Number of tasks to launch.'),
             subnet          : List[str] = typer.Option([],   '--subnet',         help='Subnet ID(s) (repeatable).'),
             sg              : List[str] = typer.Option([],   '--sg',             help='Security group ID(s) (repeatable).'),
             assign_public_ip: bool      = typer.Option(False,'--assign-public-ip', help='Assign public IP.'),
             yes             : bool      = typer.Option(False,'--yes', '-y',       help='Skip confirmation.'),
             as_json         : bool      = typer.Option(False,'--json',            help='Output as JSON.')):
    """Run a Fargate task (FARGATE launch type only)."""
    if not yes:
        typer.confirm(f'Run task "{task_def}" on cluster "{cluster}"?', abort=True)
    t = _client().run_task(cluster=cluster, task_def=task_def,
                           count=count, subnets=subnet, security_groups=sg,
                           assign_public_ip=assign_public_ip)
    if t is None:
        console.print('[red]Failed to start task.[/red]')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            task_arn     = str(t.task_arn),
            cluster_name = str(t.cluster_name),
            status       = str(t.status),
        ), indent=2))
        return
    console.print(f'[green]Started[/green] {t.task_arn}')
    console.print(f'  status: {t.status}')


# ════════════════════════════════════════════════════════════════════════════════
# task stop
# ════════════════════════════════════════════════════════════════════════════════

@task_app.command('stop')
@require_mutation_gate(_MUTATION_ENV)
def task_stop(task_arn: str  = typer.Argument(...,    help='Task ARN.'),
              cluster : str  = typer.Option('',     '--cluster', '-c', help='Cluster name.'),
              reason  : str  = typer.Option('',     '--reason',  '-r', help='Stop reason text.'),
              yes     : bool = typer.Option(False,  '--yes', '-y',      help='Skip confirmation.')):
    """Stop a running ECS task."""
    if not yes:
        typer.confirm(f'Stop task "{task_arn}"?', abort=True)
    ok = _client().stop_task(task_arn, cluster=cluster, reason=reason)
    if ok:
        console.print(f'[green]Stopped[/green] {task_arn}')
    else:
        console.print(f'[red]Failed to stop[/red] {task_arn}')
        raise typer.Exit(1)


# ════════════════════════════════════════════════════════════════════════════════
# task logs
# ════════════════════════════════════════════════════════════════════════════════

@task_app.command('logs')
def task_logs(task_arn: str  = typer.Argument(...,   help='Task ARN.'),
              cluster : str  = typer.Option('',    '--cluster', '-c', help='Cluster name.'),
              since   : str  = typer.Option('30m', '--since',   '-s', help='How far back (e.g. 30m, 1h, 2h).'),
              as_json : bool = typer.Option(False, '--json',          help='Output as JSON.')):
    """Fetch CloudWatch Logs for an ECS task (uses /ecs/<family> log group)."""
    task = _client().describe_task(task_arn, cluster=cluster)
    if task is None:
        console.print(f'[red]Task not found:[/red] {task_arn}')
        raise typer.Exit(1)

    family     = str(task.task_definition).split(':')[0]
    log_group  = _client().log_group_for_task_def(family)
    task_short = str(task.task_arn).split('/')[-1] if '/' in str(task.task_arn) else str(task.task_arn)

    start_ms   = _parse_since(since)

    from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client import Logs__AWS__Client
    logs_client = Logs__AWS__Client()
    resp = logs_client.filter_events(
        log_group      = log_group,
        start_time     = start_ms,
        log_streams    = [f'ecs/{family}/{task_short}'],
        limit          = 200,
    )

    if as_json:
        typer.echo(json.dumps([dict(
            timestamp = ev.timestamp,
            message   = ev.message,
        ) for ev in resp.events], indent=2))
        return

    if not resp.events:
        console.print(f'[dim]No log events found in {log_group}[/dim]')
        return

    for ev in resp.events:
        ts = time.strftime('%H:%M:%S', time.gmtime(ev.timestamp // 1000))
        console.print(f'[dim]{ts}[/dim]  {ev.message}', highlight=False)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_since(since: str) -> int:                                              # returns epoch ms
    now_ms = int(time.time() * 1000)
    since  = since.strip().lower()
    if since.endswith('h'):
        return now_ms - int(since[:-1]) * 3600 * 1000
    if since.endswith('m'):
        return now_ms - int(since[:-1]) * 60 * 1000
    return now_ms - 30 * 60 * 1000                                                # default 30 min
