# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Iam__Graph
# Typer group for `sg aws iam graph *` commands. Bodies owned by Slice D.
# Registered in Cli__Iam.py via iam_app.add_typer(graph_app, name='graph').
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate import require_mutation_gate

graph_app = typer.Typer(name='graph', help='IAM-as-graph discovery, filtering, and cleanup.', no_args_is_help=True)

_SLICE = "Slice D owns this body — see library/dev_packs/v0.2.29__sg-aws-iam-graph/"


@graph_app.command('discover')
def discover(account:  str  = typer.Option('', '--account'),
             region:   str  = typer.Option('', '--region'),
             as_json:  bool = typer.Option(False, '--json')):
    """Discover IAM principals, roles, and policies as a graph."""
    raise NotImplementedError(_SLICE)


@graph_app.command('show')
def show(node_id: str  = typer.Argument(..., help='Principal ARN or policy ARN.'),
         depth:   int  = typer.Option(1, '--depth'),
         as_json: bool = typer.Option(False, '--json')):
    """Show a node and its immediate graph neighbours."""
    raise NotImplementedError(_SLICE)


@graph_app.command('walk')
def walk(start:   str  = typer.Argument(..., help='Starting ARN.'),
         target:  str  = typer.Option('', '--to'),
         as_json: bool = typer.Option(False, '--json')):
    """Walk the graph from a principal to a target permission."""
    raise NotImplementedError(_SLICE)


@graph_app.command('filter')
def filter_(tag:     str  = typer.Option('', '--tag'),
            unused:  bool = typer.Option(False, '--unused'),
            no_mfa:  bool = typer.Option(False, '--no-mfa'),
            as_json: bool = typer.Option(False, '--json')):
    """Filter principals by tag, unused status, or MFA state."""
    raise NotImplementedError(_SLICE)


@graph_app.command('delete')
@require_mutation_gate('SG_AWS__IAM__ALLOW_MUTATIONS')
def delete(node_id:   str  = typer.Argument(..., help='Principal or role ARN to delete.'),
           dry_run:   bool = typer.Option(True,  '--dry-run/--no-dry-run'),
           yes:       bool = typer.Option(False, '--yes', '-y')):
    """Delete a principal from the IAM graph (gated, dry-run by default)."""
    raise NotImplementedError(_SLICE)


@graph_app.command('stats')
def stats(as_json: bool = typer.Option(False, '--json')):
    """Print graph-level statistics (node counts, edge counts, stale %)."""
    raise NotImplementedError(_SLICE)


@graph_app.command('snapshots')
def snapshots(list_:   bool = typer.Option(False, '--list'),
              restore: str  = typer.Option('', '--restore'),
              as_json: bool = typer.Option(False, '--json')):
    """Manage IAM graph snapshots (list or restore)."""
    raise NotImplementedError(_SLICE)
