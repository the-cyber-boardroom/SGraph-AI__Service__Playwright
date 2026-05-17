# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Fargate
# Typer group for `sg aws fargate *` commands.
# Bodies owned by Slice C (v0.2.29__sg-aws-fargate).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate import require_mutation_gate

app     = typer.Typer(name='fargate',  help='ECS Fargate cluster and task management.', no_args_is_help=True)
cluster = typer.Typer(name='cluster',  help='ECS cluster lifecycle.',                    no_args_is_help=True)
taskdef = typer.Typer(name='task-def', help='ECS task definition management.',           no_args_is_help=True)
task    = typer.Typer(name='task',     help='ECS task (run/stop/describe/logs).',        no_args_is_help=True)

app.add_typer(cluster, name='cluster')
app.add_typer(taskdef, name='task-def')
app.add_typer(task,    name='task')

_SLICE = "Slice C owns this body — see library/dev_packs/v0.2.29__sg-aws-fargate/"


@cluster.command('list')
def cluster_list(as_json: bool = typer.Option(False, '--json')):
    """List ECS clusters."""
    raise NotImplementedError(_SLICE)


@cluster.command('describe')
def cluster_describe(name: str = typer.Argument(...), as_json: bool = typer.Option(False, '--json')):
    """Show cluster details."""
    raise NotImplementedError(_SLICE)


@cluster.command('create')
@require_mutation_gate('SG_AWS__FARGATE__ALLOW_MUTATIONS')
def cluster_create(name: str = typer.Argument(...), yes: bool = typer.Option(False, '--yes', '-y')):
    """Create an ECS cluster (gated)."""
    raise NotImplementedError(_SLICE)


@cluster.command('delete')
@require_mutation_gate('SG_AWS__FARGATE__ALLOW_MUTATIONS')
def cluster_delete(name: str = typer.Argument(...), yes: bool = typer.Option(False, '--yes', '-y')):
    """Delete an ECS cluster (gated)."""
    raise NotImplementedError(_SLICE)


@taskdef.command('list')
def taskdef_list(family: str = typer.Option('', '--family'), as_json: bool = typer.Option(False, '--json')):
    """List task definitions."""
    raise NotImplementedError(_SLICE)


@taskdef.command('show')
def taskdef_show(family_revision: str = typer.Argument(...), as_json: bool = typer.Option(False, '--json')):
    """Show task definition details."""
    raise NotImplementedError(_SLICE)


@taskdef.command('register')
@require_mutation_gate('SG_AWS__FARGATE__ALLOW_MUTATIONS')
def taskdef_register(name:   str  = typer.Option(..., '--name'),
                     image:  str  = typer.Option(..., '--image'),
                     cpu:    int  = typer.Option(256, '--cpu'),
                     memory: int  = typer.Option(512, '--memory'),
                     yes:    bool = typer.Option(False, '--yes', '-y')):
    """Register a task definition (gated)."""
    raise NotImplementedError(_SLICE)


@task.command('list')
def task_list(cluster: str  = typer.Option('', '--cluster'),
              family:  str  = typer.Option('', '--family'),
              as_json: bool = typer.Option(False, '--json')):
    """List running tasks."""
    raise NotImplementedError(_SLICE)


@task.command('describe')
def task_describe(task_arn: str  = typer.Argument(...),
                  cluster:  str  = typer.Option('', '--cluster'),
                  as_json:  bool = typer.Option(False, '--json')):
    """Show task details."""
    raise NotImplementedError(_SLICE)


@task.command('run')
@require_mutation_gate('SG_AWS__FARGATE__ALLOW_MUTATIONS')
def task_run(cluster:  str  = typer.Option(..., '--cluster'),
             task_def: str  = typer.Option(..., '--task-def'),
             count:    int  = typer.Option(1, '--count'),
             yes:      bool = typer.Option(False, '--yes', '-y')):
    """Run a Fargate task (gated)."""
    raise NotImplementedError(_SLICE)


@task.command('stop')
@require_mutation_gate('SG_AWS__FARGATE__ALLOW_MUTATIONS')
def task_stop(task_arn: str  = typer.Argument(...),
              cluster:  str  = typer.Option('', '--cluster'),
              reason:   str  = typer.Option('', '--reason'),
              yes:      bool = typer.Option(False, '--yes', '-y')):
    """Stop a running task (gated)."""
    raise NotImplementedError(_SLICE)


@task.command('logs')
def task_logs(task_arn: str  = typer.Argument(...),
              cluster:  str  = typer.Option('', '--cluster'),
              since:    str  = typer.Option('30m', '--since'),
              as_json:  bool = typer.Option(False, '--json')):
    """Fetch CloudWatch logs for a task."""
    raise NotImplementedError(_SLICE)
