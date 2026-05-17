# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Iam
# Typer CLI surface for IAM role and policy management.
#
# Command tree:
#   sg aws iam role list   [--prefix <name>]
#   sg aws iam role show   <name>
#   sg aws iam role create <name> --trust-service <svc> [--description <text>]
#   sg aws iam role delete <name> [--yes]
#   sg aws iam role check  <name>
#   sg aws iam policy attach <role> --arn <policy-arn>
#   sg aws iam policy detach <role> --arn <policy-arn>
#   sg aws iam policy list   <role>
#
# Read-only commands (list, show, check) always allowed.
# Mutations require SG_AWS__IAM__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                              import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Audit__Severity         import Enum__IAM__Audit__Severity
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service          import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name      import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client                 import IAM__AWS__Client
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__Policy__Auditor             import IAM__Policy__Auditor
from sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph                import graph_app

console = Console()

iam_app    = typer.Typer(name='iam',    help='IAM role and policy management.',          no_args_is_help=True)
role_app   = typer.Typer(name='role',   help='IAM role lifecycle (list/show/create/…).', no_args_is_help=True)
policy_app = typer.Typer(name='policy', help='IAM inline/managed policy management.',    no_args_is_help=True)

iam_app.add_typer(role_app,   name='role')
iam_app.add_typer(policy_app, name='policy')
iam_app.add_typer(graph_app,  name='graph')


def _client() -> IAM__AWS__Client:
    return IAM__AWS__Client()


def _mutation_guard():
    if not os.environ.get('SG_AWS__IAM__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__IAM__ALLOW_MUTATIONS=1 to allow IAM mutations.[/red]')
        raise typer.Exit(1)


def _severity_style(severity: Enum__IAM__Audit__Severity) -> str:
    return {'INFO': 'dim', 'WARN': 'yellow', 'CRITICAL': 'red'}[str(severity)]


# ── role list ─────────────────────────────────────────────────────────────────

@role_app.command('list')
@spec_cli_errors
def role_list(prefix  : str  = typer.Option('',    '--prefix', '-p', help='Filter by role name prefix.'),
              as_json : bool = typer.Option(False, '--json',          help='Output as JSON.')):
    """List IAM roles, optionally filtered by name prefix."""
    roles = _client().list_roles(prefix=prefix)
    if as_json:
        typer.echo(json.dumps([dict(role_name  =str(r.role_name),
                                    role_arn   =str(r.role_arn),
                                    trust      =str(r.trust_service),
                                    created_at =r.created_at) for r in roles], indent=2))
        return
    if not roles:
        console.print('No IAM roles found.')
        return
    t = Table(title='IAM Roles')
    t.add_column('Name',       style='cyan')
    t.add_column('Trust',      style='green')
    t.add_column('Created',    style='dim')
    for r in roles:
        t.add_row(str(r.role_name), str(r.trust_service), r.created_at[:10] if r.created_at else '—')
    console.print(t)


# ── role show ─────────────────────────────────────────────────────────────────

@role_app.command('show')
@spec_cli_errors
def role_show(name    : str  = typer.Argument(...,  help='IAM role name.'),
              as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show details and inline policies for an IAM role."""
    role = _client().get_role(name)
    if role is None:
        console.print(f'[red]Role not found:[/red] {name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(role_name          = str(role.role_name),
                                   role_arn           = str(role.role_arn),
                                   trust_service      = str(role.trust_service),
                                   created_at         = role.created_at,
                                   last_used          = role.last_used,
                                   inline_policy_count= len(role.inline_policies),
                                   managed_policy_count=len(role.managed_policy_arns)), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=20)
    t.add_column()
    t.add_row('name',           str(role.role_name))
    t.add_row('arn',            str(role.role_arn))
    t.add_row('trust',          str(role.trust_service))
    t.add_row('created',        role.created_at or '—')
    t.add_row('last used',      role.last_used or '—')
    t.add_row('inline policies',str(len(role.inline_policies)))
    t.add_row('managed policies',str(len(role.managed_policy_arns)))
    console.print()
    console.print(t)
    console.print()


# ── role create ───────────────────────────────────────────────────────────────

@role_app.command('create')
@spec_cli_errors
def role_create(name          : str  = typer.Argument(..., help='IAM role name.'),
                trust_service : str  = typer.Option('lambda', '--trust-service', '-t',
                                                    help='Trust service: lambda, ec2, ecs-tasks, api-gateway.'),
                description   : str  = typer.Option('',    '--description', '-d', help='Role description.'),
                as_json       : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Create an IAM role with the specified trust service."""
    _mutation_guard()
    trust_map = {
        'lambda'     : Enum__IAM__Trust__Service.LAMBDA,
        'ec2'        : Enum__IAM__Trust__Service.EC2,
        'ecs-tasks'  : Enum__IAM__Trust__Service.ECS_TASKS,
        'api-gateway': Enum__IAM__Trust__Service.API_GATEWAY,
    }
    if trust_service not in trust_map:
        console.print(f'[red]Unknown trust service:[/red] {trust_service}')
        raise typer.Exit(1)
    req  = Schema__IAM__Role__Create__Request(
        role_name    = Safe_Str__IAM__Role_Name(name),
        trust_service= trust_map[trust_service],
        description  = description,
    )
    resp = _client().create_role(req)
    if as_json:
        typer.echo(json.dumps(dict(role_name=str(resp.role_name),
                                   role_arn =str(resp.role_arn),
                                   created  =resp.created,
                                   message  =resp.message), indent=2))
        return
    verb = 'Created' if resp.created else 'Already exists'
    console.print(f'[green]{verb}[/green] {name}')
    console.print(f'  ARN: {resp.role_arn}')


# ── role delete ───────────────────────────────────────────────────────────────

@role_app.command('delete')
@spec_cli_errors
def role_delete(name   : str  = typer.Argument(...,   help='IAM role name.'),
                yes    : bool = typer.Option(False,  '--yes', '-y', help='Skip confirmation prompt.'),
                as_json: bool = typer.Option(False,  '--json', help='Output as JSON.')):
    """Delete an IAM role (detaches all policies first)."""
    _mutation_guard()
    if not yes:
        typer.confirm(f'Delete role "{name}"?', abort=True)
    ok = _client().delete_role(name)
    if as_json:
        typer.echo(json.dumps({'deleted': ok, 'role_name': name}))
        return
    if ok:
        console.print(f'[green]Deleted[/green] {name}')
    else:
        console.print(f'[red]Failed to delete[/red] {name}')
        raise typer.Exit(1)


# ── role check ────────────────────────────────────────────────────────────────

@role_app.command('check')
@spec_cli_errors
def role_check(name    : str  = typer.Argument(...,   help='IAM role name.'),
               as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Audit an IAM role for over-permissive grants. Exit 0=clean, 1=WARN, 2=CRITICAL."""
    role = _client().get_role(name)
    if role is None:
        console.print(f'[red]Role not found:[/red] {name}')
        raise typer.Exit(2)
    report = IAM__Policy__Auditor().audit(role)
    if as_json:
        typer.echo(json.dumps(dict(
            role_name        = str(report.role_name),
            overall_severity = str(report.overall_severity),
            passed_count     = report.passed_count,
            failed_count     = report.failed_count,
            findings         = [dict(severity        =str(f.severity),
                                     code            =str(f.code),
                                     statement_index =f.statement_index,
                                     message         =f.message,
                                     remediation_hint=f.remediation_hint)
                                for f in report.findings],
        ), indent=2))
    else:
        console.print()
        console.print(f'  Audit: [bold]{name}[/bold]  —  severity: [{_severity_style(report.overall_severity)}]{report.overall_severity}[/]')
        console.print()
        if not report.findings:
            console.print('  [green]✓  No findings[/green]')
        else:
            t = Table(box=None, show_header=True, padding=(0, 2))
            t.add_column('Sev',     style='bold', min_width=8)
            t.add_column('Code',    min_width=25)
            t.add_column('Message')
            t.add_column('Hint',    style='dim')
            for f in sorted(report.findings, key=lambda x: {'CRITICAL':0,'WARN':1,'INFO':2}[str(x.severity)]):
                t.add_row(f'[{_severity_style(f.severity)}]{f.severity}[/]',
                          str(f.code), f.message, f.remediation_hint)
            console.print(t)
        console.print()

    exit_code = {'INFO': 0, 'WARN': 1, 'CRITICAL': 2}[str(report.overall_severity)]
    if exit_code:
        raise typer.Exit(exit_code)


# ── policy attach ─────────────────────────────────────────────────────────────

@policy_app.command('attach')
@spec_cli_errors
def policy_attach(role    : str  = typer.Argument(..., help='IAM role name.'),
                  arn     : str  = typer.Option(...,  '--arn', help='Managed policy ARN to attach.')):
    """Attach a managed policy to an IAM role."""
    _mutation_guard()
    ok = _client().attach_managed_policy(role, arn)
    if ok:
        console.print(f'[green]Attached[/green] {arn} → {role}')
    else:
        console.print(f'[red]Failed[/red]')
        raise typer.Exit(1)


# ── policy detach ─────────────────────────────────────────────────────────────

@policy_app.command('detach')
@spec_cli_errors
def policy_detach(role    : str  = typer.Argument(..., help='IAM role name.'),
                  arn     : str  = typer.Option(...,  '--arn', help='Managed policy ARN to detach.')):
    """Detach a managed policy from an IAM role."""
    _mutation_guard()
    ok = _client().detach_managed_policy(role, arn)
    if ok:
        console.print(f'[green]Detached[/green] {arn} from {role}')
    else:
        console.print(f'[red]Failed[/red]')
        raise typer.Exit(1)


# ── policy list ───────────────────────────────────────────────────────────────

@policy_app.command('list')
@spec_cli_errors
def policy_list(role    : str  = typer.Argument(...,   help='IAM role name.'),
                as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List inline and managed policies attached to an IAM role."""
    r = _client().get_role(role)
    if r is None:
        console.print(f'[red]Role not found:[/red] {role}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(inline_count  =len(r.inline_policies),
                                   managed_arns   =[str(a) for a in r.managed_policy_arns]), indent=2))
        return
    console.print(f'\n  Role: [bold]{role}[/bold]')
    console.print(f'  Inline policies : {len(r.inline_policies)}')
    console.print(f'  Managed policies: {len(r.managed_policy_arns)}')
    for arn in r.managed_policy_arns:
        console.print(f'    • {arn}')
    console.print()
