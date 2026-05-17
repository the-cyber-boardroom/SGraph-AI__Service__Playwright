# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Iam__Graph
# Typer surface for `sg aws iam graph *` commands.
# Registered in Cli__Iam.py via iam_app.add_typer(graph_app, name='graph').
#
# Command tree:
#   sg aws iam graph discover         [--json]
#   sg aws iam graph show             [--snapshot ID] [--json]
#   sg aws iam graph walk ROOT        [--depth N] [--json]
#   sg aws iam graph filter           --unused [--days N] / --pattern GLOB /
#                                     --aws-default  [--output FILE] [--json]
#   sg aws iam graph delete           --from FILE [--confirm] [--yes]
#   sg aws iam graph stats            [--snapshot ID] [--json]
#   sg aws iam graph snapshots list   [--json]
#   sg aws iam graph snapshots diff A B [--json]
#
# HIGH BLAST-RADIUS — `delete` requires BOTH SG_AWS__IAM__ALLOW_MUTATIONS=1
# AND --confirm flag. Dry-run is the hard default.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import random
import string
from datetime import datetime, timezone
from pathlib  import Path
from typing   import Optional

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                                   import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm                             import confirm_or_abort
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate                           import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Discovery__Orchestrator  import Iam__Discovery__Orchestrator
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Builder           import Iam__Graph__Builder
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Filter            import Iam__Graph__Filter
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer     import Iam__Graph__Vault__Writer
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Snapshot__Diff    import Iam__Graph__Snapshot__Diff
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Cleanup           import Iam__Graph__Cleanup
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Walker            import Iam__Graph__Walker

console      = Console()
graph_app    = typer.Typer(name='graph',     help='IAM-as-graph discovery, filtering, and cleanup.', no_args_is_help=True)
snapshot_app = typer.Typer(name='snapshots', help='Manage IAM graph snapshots.',                      no_args_is_help=True)
graph_app.add_typer(snapshot_app, name='snapshots')

_IAM_MUTATIONS_ENV = 'SG_AWS__IAM__ALLOW_MUTATIONS'


def _make_snapshot_id() -> str:
    ts    = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    nonce = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f'{ts}__{nonce}'


def _default_orchestrator() -> Iam__Discovery__Orchestrator:
    return Iam__Discovery__Orchestrator()


def _default_writer() -> Iam__Graph__Vault__Writer:
    return Iam__Graph__Vault__Writer()


# ── discover ──────────────────────────────────────────────────────────────────

@graph_app.command('discover')
@spec_cli_errors
def discover(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Pull current IAM state into a local snapshot."""
    orchestrator = _default_orchestrator()
    writer       = _default_writer()
    builder      = Iam__Graph__Builder()

    snapshot_id  = _make_snapshot_id()
    captured_at  = datetime.now(tz=timezone.utc).isoformat()

    nodes = orchestrator.discover_nodes()
    edges = orchestrator.discover_edges(nodes)
    meta  = builder.build_snapshot_meta(
        snapshot_id = snapshot_id,
        nodes       = nodes,
        edges       = edges,
        captured_at = captured_at,
    )
    snap_dir = writer.write(snapshot_meta=meta, nodes=nodes, edges=edges)

    if as_json:
        typer.echo(json.dumps(dict(
            snapshot_id  = snapshot_id,
            captured_at  = captured_at,
            role_count   = meta.role_count,
            edge_count   = meta.edge_count,
            path         = str(snap_dir),
        ), indent=2))
    else:
        console.print(f'[green]Snapshot captured:[/green] {snapshot_id}')
        console.print(f'  roles:  {meta.role_count}')
        console.print(f'  edges:  {meta.edge_count}')
        console.print(f'  path:   {snap_dir}')


# ── show ──────────────────────────────────────────────────────────────────────

@graph_app.command('show')
@spec_cli_errors
def show(snapshot_id : Optional[str] = typer.Option(None, '--snapshot', help='Snapshot ID; defaults to latest.'),
         as_json     : bool           = typer.Option(False, '--json',    help='Output as JSON.')):
    """Show summary of an IAM graph snapshot."""
    writer = _default_writer()
    snap   = snapshot_id or writer.latest_snapshot_id()
    if not snap:
        console.print('[red]No snapshots found. Run `sg aws iam graph discover` first.[/red]')
        raise typer.Exit(1)
    data = writer.load_snapshot(snap)
    if not data:
        console.print(f'[red]Snapshot not found:[/red] {snap}')
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(data, indent=2))
        return

    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18)
    t.add_column()
    t.add_row('snapshot_id',  data.get('snapshot_id', ''))
    t.add_row('captured_at',  data.get('captured_at', ''))
    t.add_row('roles',        str(data.get('role_count', 0)))
    t.add_row('policies',     str(data.get('policy_count', 0)))
    t.add_row('users',        str(data.get('user_count', 0)))
    t.add_row('groups',       str(data.get('group_count', 0)))
    t.add_row('edges',        str(data.get('edge_count', 0)))
    t.add_row('account',      data.get('aws_account_id', '—'))
    t.add_row('region',       data.get('region', '—'))
    console.print()
    console.print(t)
    console.print()


# ── walk ──────────────────────────────────────────────────────────────────────

@graph_app.command('walk')
@spec_cli_errors
def walk(root       : str  = typer.Argument(...,   help='Root node ID (ARN or role name).'),
         depth      : int  = typer.Option(3,       '--depth', '-d', help='Max traversal depth.'),
         snapshot_id: Optional[str] = typer.Option(None, '--snapshot', help='Snapshot ID; defaults to latest.'),
         as_json    : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Transitive permission walk from a root IAM node."""
    writer = _default_writer()
    snap   = snapshot_id or writer.latest_snapshot_id()
    if not snap:
        console.print('[red]No snapshots found. Run `sg aws iam graph discover` first.[/red]')
        raise typer.Exit(1)
    nodes = writer.load_nodes(snap)
    edges = writer.load_edges(snap)

    # Allow walk by name OR by ARN/node_id
    resolved_root = root
    for n in nodes:
        if n.get('name') == root or n.get('arn') == root:
            resolved_root = n['node_id']
            break

    result = Iam__Graph__Walker().walk(resolved_root, nodes, edges, max_depth=depth)
    if as_json:
        typer.echo(json.dumps(result, indent=2))
        return
    console.print(f'\n  Walk from [bold]{root}[/bold]  (depth={depth})\n')
    t = Table('depth', 'type', 'name', 'node_id', box=None, padding=(0, 2))
    for n in result['nodes']:
        t.add_row(str(n.get('walk_depth', '')), n.get('node_type', ''), n.get('name', ''), n.get('node_id', ''))
    console.print(t)
    console.print()


# ── filter ────────────────────────────────────────────────────────────────────

@graph_app.command('filter')
@spec_cli_errors
def filter_nodes(
    unused      : bool          = typer.Option(False, '--unused',      help='Filter roles with no recent activity.'),
    days        : int           = typer.Option(90,    '--days',        help='Inactivity threshold in days (with --unused).'),
    pattern     : Optional[str] = typer.Option(None,  '--pattern',     help='Glob pattern for role name.'),
    aws_default : bool          = typer.Option(False, '--aws-default', help='Filter AWS-auto-created / service-linked roles.'),
    output      : Optional[str] = typer.Option(None,  '--output',  '-o', help='Write candidates JSON to file.'),
    snapshot_id : Optional[str] = typer.Option(None,  '--snapshot',    help='Snapshot ID; defaults to latest.'),
    as_json     : bool          = typer.Option(False, '--json',        help='Output as JSON.'),
):
    """Filter IAM nodes by unused / pattern / aws-default predicate."""
    writer = _default_writer()
    snap   = snapshot_id or writer.latest_snapshot_id()
    if not snap:
        console.print('[red]No snapshots found. Run `sg aws iam graph discover` first.[/red]')
        raise typer.Exit(1)

    raw_nodes = writer.load_nodes(snap)

    from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node   import Schema__IAM__Graph__Node
    from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id import Safe_Str__IAM__Node__Id
    from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type        import Enum__IAM__Node__Type
    from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth    import Enum__IAM__Scope__Breadth
    from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node

    nodes = List__Schema__IAM__Graph__Node()
    for raw in raw_nodes:
        try:
            node = Schema__IAM__Graph__Node(
                node_id          = Safe_Str__IAM__Node__Id(raw['node_id']),
                node_type        = Enum__IAM__Node__Type(raw.get('node_type', 'role')),
                name             = raw.get('name', ''),
                arn              = raw.get('arn', ''),
                created_at       = raw.get('created_at', ''),
                last_used        = raw.get('last_used', ''),
                scope_breadth    = Enum__IAM__Scope__Breadth(raw.get('scope_breadth', 'specific')),
                is_aws_default   = raw.get('is_aws_default', False),
                is_service_linked= raw.get('is_service_linked', False),
                trust_principal  = raw.get('trust_principal', ''),
                tags_json        = raw.get('tags_json', ''),
            )
            nodes.append(node)
        except Exception:
            continue

    flt        = Iam__Graph__Filter()
    candidates = nodes
    if unused:
        candidates = flt.filter_unused(candidates, days=days)
    elif pattern:
        candidates = flt.filter_pattern(candidates, pattern)
    elif aws_default:
        candidates = flt.filter_aws_default(candidates)

    candidates_dicts = [dict(
        node_id          = str(n.node_id),
        node_type        = str(n.node_type),
        name             = n.name,
        arn              = n.arn,
        created_at       = n.created_at,
        last_used        = n.last_used,
        scope_breadth    = str(n.scope_breadth),
        is_aws_default   = n.is_aws_default,
        is_service_linked= n.is_service_linked,
        trust_principal  = n.trust_principal,
    ) for n in candidates]

    payload = dict(snapshot_id=snap, candidates=candidates_dicts, count=len(candidates_dicts))

    if output:
        Path(output).write_text(json.dumps(payload, indent=2))
        console.print(f'[green]Written[/green] {len(candidates_dicts)} candidates → {output}')

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    if not output:
        console.print(f'\n  Filter result from [bold]{snap}[/bold]: {len(candidates_dicts)} candidates\n')
        if candidates_dicts:
            t = Table('name', 'type', 'last_used', 'aws_default', box=None, padding=(0, 2))
            for c in candidates_dicts:
                t.add_row(c['name'], c['node_type'],
                          c['last_used'][:10] if c['last_used'] else '(never)',
                          str(c['is_aws_default']))
            console.print(t)
        console.print()


# ── delete ────────────────────────────────────────────────────────────────────

@graph_app.command('delete')
@require_mutation_gate(_IAM_MUTATIONS_ENV)
@spec_cli_errors
def delete_roles(
    from_file : str  = typer.Option(...,  '--from',     help='Path to candidate JSON file (output of filter).'),
    confirm   : bool = typer.Option(False, '--confirm',  help='Actually delete (omit for dry-run).'),
    yes       : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation prompt.'),
    dry_run   : bool = typer.Option(False, '--dry-run',  help='Print would-be deletion without executing.'),
    as_json   : bool = typer.Option(False, '--json',     help='Output as JSON.'),
):
    """Delete IAM roles from a candidate file. Dry-run by default; --confirm to mutate.

    AppSec: HIGH BLAST-RADIUS. Requires SG_AWS__IAM__ALLOW_MUTATIONS=1 AND --confirm.
    Service-linked roles are skipped automatically.
    """
    candidates_file = Path(from_file)
    if not candidates_file.exists():
        console.print(f'[red]File not found:[/red] {from_file}')
        raise typer.Exit(1)
    data = json.loads(candidates_file.read_text())
    raw_candidates = data.get('candidates', data) if isinstance(data, dict) else data

    cleanup = Iam__Graph__Cleanup()
    plan    = cleanup.build_plan(raw_candidates)

    if not confirm:
        payload = dict(
            dry_run               = True,
            candidate_count       = len(plan.candidates),
            skipped_service_linked= plan.skipped_service_linked,
            executed              = False,
            deleted_count         = 0,
            error_count           = 0,
            message               = 'Dry-run. Pass --confirm to actually delete.',
        )
        if as_json:
            typer.echo(json.dumps(payload, indent=2))
        else:
            console.print('\n  [yellow]Dry-run[/yellow] — no changes made.')
            console.print(f'  Candidates       : {len(plan.candidates)}')
            console.print(f'  Skipped (svc-lnk): {plan.skipped_service_linked}')
            console.print('\n  Pass [bold]--confirm[/bold] to actually delete.\n')
        return

    # ── real deletion path ────────────────────────────────────────────────────
    if not confirm_or_abort(f'Delete {len(plan.candidates)} IAM roles?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)

    executed = cleanup.execute_plan(plan, confirm=True)
    payload  = dict(
        dry_run         = False,
        candidate_count = len(plan.candidates),
        deleted_count   = executed.deleted_count,
        error_count     = executed.error_count,
        executed        = True,
    )
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(f'\n  [green]Deleted[/green]  : {executed.deleted_count}')
        console.print(f'  [red]Errors[/red]   : {executed.error_count}\n')


# ── stats ─────────────────────────────────────────────────────────────────────

@graph_app.command('stats')
@spec_cli_errors
def stats(snapshot_id : Optional[str] = typer.Option(None, '--snapshot', help='Snapshot ID; defaults to latest.'),
          as_json     : bool           = typer.Option(False, '--json',    help='Output as JSON.')):
    """Scope-breadth histogram for an IAM graph snapshot."""
    writer = _default_writer()
    snap   = snapshot_id or writer.latest_snapshot_id()
    if not snap:
        console.print('[red]No snapshots found. Run `sg aws iam graph discover` first.[/red]')
        raise typer.Exit(1)
    nodes = writer.load_nodes(snap)

    breadth_counts = {}
    for n in nodes:
        sb = n.get('scope_breadth', 'specific')
        breadth_counts[sb] = breadth_counts.get(sb, 0) + 1

    total = len(nodes)
    payload = dict(snapshot_id=snap, total=total, by_scope_breadth=breadth_counts)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    console.print(f'\n  Stats for [bold]{snap}[/bold]  (total nodes: {total})\n')
    t = Table('scope_breadth', 'count', box=None, padding=(0, 2))
    for k, v in sorted(breadth_counts.items()):
        t.add_row(k, str(v))
    console.print(t)
    console.print()


# ── snapshots list ────────────────────────────────────────────────────────────

@snapshot_app.command('list')
@spec_cli_errors
def snapshots_list(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List all IAM graph snapshots."""
    writer = _default_writer()
    snaps  = writer.list_snapshots()
    if as_json:
        typer.echo(json.dumps(snaps, indent=2))
        return
    if not snaps:
        console.print('No snapshots found.')
        return
    t = Table('snapshot_id', 'captured_at', 'roles', 'edges', box=None, padding=(0, 2))
    for s in snaps:
        t.add_row(s.get('snapshot_id', ''),
                  s.get('captured_at', '')[:19],
                  str(s.get('role_count', 0)),
                  str(s.get('edge_count', 0)))
    console.print()
    console.print(t)
    console.print()


# ── snapshots diff ────────────────────────────────────────────────────────────

@snapshot_app.command('diff')
@spec_cli_errors
def snapshots_diff(snapshot_a : str  = typer.Argument(..., help='Earlier snapshot ID.'),
                   snapshot_b : str  = typer.Argument(..., help='Later snapshot ID.'),
                   as_json    : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Diff two IAM graph snapshots."""
    writer = _default_writer()
    result = Iam__Graph__Snapshot__Diff(vault_writer=writer).diff(snapshot_a, snapshot_b)
    if as_json:
        typer.echo(json.dumps(result, indent=2))
        return
    console.print(f'\n  Diff: [bold]{snapshot_a}[/bold] → [bold]{snapshot_b}[/bold]\n')
    console.print(f'  Added nodes   : {len(result["added_nodes"])}')
    console.print(f'  Removed nodes : {len(result["removed_nodes"])}')
    console.print(f'  Added edges   : {len(result["added_edges"])}')
    console.print(f'  Removed edges : {len(result["removed_edges"])}')
    console.print(f'  Node delta    : {result["node_delta"]:+}')
    console.print()
