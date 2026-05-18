# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Ecr
# Typer CLI surface for `sg aws ecr *` commands.
#
# Command tree:
#   sg aws ecr repos                                           [--json]
#   sg aws ecr repo        <name>                              [--json]
#   sg aws ecr images      <repo> [--untagged] [--digest] [--older 30d] [--json]
#   sg aws ecr image       <repo> <tag-or-digest>              [--json]
#   sg aws ecr scan        <repo> <tag-or-digest>              [--json]
#   sg aws ecr prune       <repo> [--untagged] [--older 30d] [--keep-last 5]
#                                 [--dry-run] [--yes] [--json]      (mutating)
#   sg aws ecr delete      <repo> <tag-or-digest> [--yes] [--json]  (mutating)
#   sg aws ecr repo-create <name>                          [--json] (mutating)
#   sg aws ecr repo-delete <name> [--force] [--yes]        [--json] (mutating)
#
# Mutating commands require SG_AWS__ECR__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import re
from datetime import datetime, timedelta, timezone

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate           import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client     import ECR__AWS__Client
from sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__Prune__Planner  import ECR__Prune__Planner

_MUTATION_ENV = 'SG_AWS__ECR__ALLOW_MUTATIONS'

console = Console()

app = typer.Typer(name='ecr', help='ECR repository and image management.',
                  no_args_is_help=True)


# ── helpers ───────────────────────────────────────────────────────────────────

_TTL_RE = re.compile(r'^(\d+)\s*([smhd])$')                                      # 30d, 12h, 5m, 30s


def _parse_older(value: str) -> timedelta:                                       # Raises typer.BadParameter on bad input
    if not value:
        return timedelta(0)
    m = _TTL_RE.match(value.strip())
    if not m:
        raise typer.BadParameter(f"--older must be like '30d', '12h', '5m'; got {value!r}")
    n, unit = int(m.group(1)), m.group(2)
    if unit == 's': return timedelta(seconds=n)
    if unit == 'm': return timedelta(minutes=n)
    if unit == 'h': return timedelta(hours=n)
    return timedelta(days=n)


def _parse_pushed_at(s: str):                                                    # str → aware datetime or None
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _setup_ctx_client(ctx: typer.Context):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj.setdefault('ecr_client', ECR__AWS__Client())


@app.callback()
def _setup_ctx(ctx: typer.Context):
    _setup_ctx_client(ctx)


# ── repos ─────────────────────────────────────────────────────────────────────

@app.command('repos')
@spec_cli_errors
def ecr_repos(ctx     : typer.Context,
              as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List ECR repositories in the current region."""
    client = ctx.obj['ecr_client']
    repos  = client.list_repositories()
    if as_json:
        typer.echo(json.dumps([dict(name                 = str(r.name),
                                     arn                  = str(r.arn),
                                     registry_id          = str(r.registry_id),
                                     created_at           = str(r.created_at),
                                     image_tag_mutability = str(r.image_tag_mutability),
                                     scan_on_push         = bool(r.scan_on_push))
                                for r in repos], indent=2))
        return
    if not repos:
        console.print('No repositories found.')
        return
    t = Table(title='ECR Repositories')
    t.add_column('Name',         style='cyan')
    t.add_column('Mutability',   style='dim')
    t.add_column('Scan on Push', style='dim')
    t.add_column('Created',      style='dim')
    for r in repos:
        t.add_row(str(r.name),
                  str(r.image_tag_mutability) or '—',
                  'yes' if r.scan_on_push else 'no',
                  str(r.created_at) or '—')
    console.print(t)


# ── repo ──────────────────────────────────────────────────────────────────────

@app.command('repo')
@spec_cli_errors
def ecr_repo(ctx     : typer.Context,
             name    : str  = typer.Argument(..., help='Repository name.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show a repository summary: image count, total bytes, lifecycle policy."""
    repo = ctx.obj['ecr_client'].describe_repository(name)
    if repo is None:
        console.print(f'[red]Repository not found:[/red] {name}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            name                 = str(repo.name),
            arn                  = str(repo.arn),
            registry_id          = str(repo.registry_id),
            created_at           = str(repo.created_at),
            image_count          = int(repo.image_count),
            total_size_bytes     = int(repo.total_size_bytes),
            lifecycle_policy     = str(repo.lifecycle_policy),
            image_tag_mutability = str(repo.image_tag_mutability),
            scan_on_push         = bool(repo.scan_on_push),
        ), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('name',             str(repo.name)),
        ('arn',              str(repo.arn)             or '—'),
        ('registry id',      str(repo.registry_id)     or '—'),
        ('created',          str(repo.created_at)      or '—'),
        ('image count',      str(repo.image_count)),
        ('total bytes',      str(repo.total_size_bytes)),
        ('tag mutability',   str(repo.image_tag_mutability) or '—'),
        ('scan on push',     'yes' if repo.scan_on_push else 'no'),
        ('lifecycle policy', str(repo.lifecycle_policy) or '(none)'),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── images ────────────────────────────────────────────────────────────────────

@app.command('images')
@spec_cli_errors
def ecr_images(ctx       : typer.Context,
               repo      : str  = typer.Argument(..., help='Repository name.'),
               untagged  : bool = typer.Option(False, '--untagged',
                                                help='Only images with no tags.'),
               show_digest: bool = typer.Option(False, '--digest',
                                                help='Show full digest column.'),
               older     : str  = typer.Option('',    '--older',
                                                help='Only images pushed before TTL (e.g. 30d).'),
               as_json   : bool = typer.Option(False, '--json',
                                                help='Output as JSON.')):
    """List images in an ECR repository (sorted newest first)."""
    client = ctx.obj['ecr_client']
    images = client.list_images(repo, untagged=untagged)
    if images is None:
        console.print(f'[red]Repository not found:[/red] {repo}')
        raise typer.Exit(1)
    # ── filter by --older TTL ─────────────────────────────────────────────────
    if older:
        delta  = _parse_older(older)
        cutoff = datetime.now(timezone.utc) - delta
        kept   = []
        for img in images:
            pushed_dt = _parse_pushed_at(str(img.pushed_at))
            if pushed_dt is None:
                continue
            if pushed_dt.tzinfo is None:
                pushed_dt = pushed_dt.replace(tzinfo=timezone.utc)
            if pushed_dt <= cutoff:
                kept.append(img)
        filtered = kept
    else:
        filtered = list(images)
    # ── sort newest first ────────────────────────────────────────────────────
    filtered.sort(key=lambda i: str(i.pushed_at), reverse=True)
    if as_json:
        typer.echo(json.dumps([dict(repo_name           = str(i.repo_name),
                                     digest              = str(i.digest),
                                     tags                = [str(t) for t in i.tags],
                                     size_bytes          = int(i.size_bytes),
                                     pushed_at           = str(i.pushed_at),
                                     manifest_media_type = str(i.manifest_media_type),
                                     scan_status         = str(i.scan_status))
                                for i in filtered], indent=2))
        return
    if not filtered:
        console.print('No images found.')
        return
    t = Table(title=f'ECR Images — {repo}')
    t.add_column('Tags',     style='cyan')
    t.add_column('Pushed',   style='dim')
    t.add_column('Size',     style='dim', justify='right')
    t.add_column('Scan',     style='dim')
    if show_digest:
        t.add_column('Digest', style='dim')
    for i in filtered:
        tag_str = ', '.join(str(x) for x in i.tags) or '(untagged)'
        size_mb = f'{i.size_bytes / (1024 * 1024):.1f} MiB' if i.size_bytes else '—'
        row     = [tag_str, str(i.pushed_at) or '—', size_mb, str(i.scan_status)]
        if show_digest:
            row.append(str(i.digest))
        t.add_row(*row)
    console.print(t)


# ── image ─────────────────────────────────────────────────────────────────────

@app.command('image')
@spec_cli_errors
def ecr_image(ctx           : typer.Context,
              repo          : str  = typer.Argument(..., help='Repository name.'),
              tag_or_digest : str  = typer.Argument(..., help='Image tag or sha256: digest.'),
              as_json       : bool = typer.Option(False, '--json',
                                                   help='Output as JSON.')):
    """Show full detail for one ECR image."""
    img = ctx.obj['ecr_client'].describe_image(repo, tag_or_digest)
    if img is None:
        console.print(f'[red]Image not found:[/red] {repo} {tag_or_digest}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(dict(
            repo_name           = str(img.repo_name),
            digest              = str(img.digest),
            tags                = [str(t) for t in img.tags],
            size_bytes          = int(img.size_bytes),
            pushed_at           = str(img.pushed_at),
            manifest_media_type = str(img.manifest_media_type),
            scan_status         = str(img.scan_status),
        ), indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=22)
    t.add_column()
    rows = [
        ('repo',           str(img.repo_name)),
        ('digest',         str(img.digest)),
        ('tags',           ', '.join(str(x) for x in img.tags) or '(untagged)'),
        ('size bytes',     str(img.size_bytes)),
        ('pushed',         str(img.pushed_at)            or '—'),
        ('manifest media', str(img.manifest_media_type)  or '—'),
        ('scan status',    str(img.scan_status)),
    ]
    for label, value in rows:
        t.add_row(label, value)
    console.print()
    console.print(t)
    console.print()


# ── scan ──────────────────────────────────────────────────────────────────────

@app.command('scan')
@spec_cli_errors
def ecr_scan(ctx           : typer.Context,
             repo          : str  = typer.Argument(..., help='Repository name.'),
             tag_or_digest : str  = typer.Argument(..., help='Image tag or sha256: digest.'),
             as_json       : bool = typer.Option(False, '--json',
                                                  help='Output as JSON.')):
    """Show the most-recent scan findings for an ECR image."""
    findings = ctx.obj['ecr_client'].get_image_scan_findings(repo, tag_or_digest)
    if findings is None:
        console.print(f'[yellow]No scan findings (or image not found):[/yellow] '
                      f'{repo} {tag_or_digest}')
        raise typer.Exit(1)
    counts = findings.counts
    if as_json:
        typer.echo(json.dumps(dict(
            repo_name    = str(findings.repo_name),
            digest       = str(findings.digest),
            status       = str(findings.status),
            completed_at = str(findings.completed_at),
            counts       = dict(critical      = int(counts.critical),
                                high          = int(counts.high),
                                medium        = int(counts.medium),
                                low           = int(counts.low),
                                informational = int(counts.informational),
                                undefined     = int(counts.undefined)),
        ), indent=2))
        return
    console.print()
    console.print(f'  [bold]repo[/bold]      : {findings.repo_name}')
    console.print(f'  [bold]digest[/bold]    : {findings.digest}')
    console.print(f'  [bold]status[/bold]    : {findings.status}')
    console.print(f'  [bold]completed[/bold] : {findings.completed_at or "—"}')
    console.print()
    t = Table(title='Severity counts')
    t.add_column('Severity', style='bold')
    t.add_column('Count',    justify='right')
    t.add_row('CRITICAL',      f'[red]{counts.critical}[/red]')
    t.add_row('HIGH',          f'[red]{counts.high}[/red]')
    t.add_row('MEDIUM',        f'[yellow]{counts.medium}[/yellow]')
    t.add_row('LOW',           str(counts.low))
    t.add_row('INFORMATIONAL', str(counts.informational))
    t.add_row('UNDEFINED',     str(counts.undefined))
    console.print(t)
    console.print()


# ── prune ─────────────────────────────────────────────────────────────────────

@app.command('prune')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ecr_prune(ctx       : typer.Context,
              repo      : str  = typer.Argument(..., help='Repository name.'),
              untagged  : bool = typer.Option(False, '--untagged',
                                              help='Restrict candidates to images with no tags.'),
              older     : str  = typer.Option('',    '--older',
                                              help='Only images pushed before TTL (e.g. 30d).'),
              keep_last : int  = typer.Option(0,     '--keep-last',
                                              help='Protect N most-recent tagged images.'),
              dry_run   : bool = typer.Option(False, '--dry-run',
                                              help='Show plan but do not delete.'),
              yes       : bool = typer.Option(False, '--yes',
                                              help='Skip confirmation prompt.'),
              as_json   : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Prune ECR images by policy (requires SG_AWS__ECR__ALLOW_MUTATIONS=1)."""
    client = ctx.obj['ecr_client']
    images = client.list_images(repo)
    if images is None:
        console.print(f'[red]Repository not found:[/red] {repo}')
        raise typer.Exit(1)
    older_td = _parse_older(older) if older else None
    plan = ECR__Prune__Planner().plan(images     = images,
                                      untagged   = untagged,
                                      older_than = older_td,
                                      keep_last  = keep_last,
                                      now        = datetime.now(timezone.utc),
                                      repo_name  = repo)
    # ── JSON output (dry-run or not, the executed flag tracks state) ─────────
    if as_json:
        executed      = False
        deleted_count = 0
        if not dry_run:
            if not yes and not typer.confirm(
                f'Delete {len(plan.to_delete)} images? This cannot be undone.', default=False):
                executed = False
            else:
                digests       = [str(img.digest) for img in plan.to_delete if str(img.digest)]
                deleted_count = client.batch_delete_images(repo, digests)
                executed      = True
        typer.echo(json.dumps({'plan'         : plan.json(),
                               'executed'     : executed,
                               'deleted_count': deleted_count}, indent=2, default=str))
        return
    # ── table output ─────────────────────────────────────────────────────────
    if plan.to_delete:
        t = Table(title=f'ECR Prune Plan — {repo}')
        t.add_column('Digest',  style='dim')
        t.add_column('Tags',    style='cyan')
        t.add_column('Size',    style='dim', justify='right')
        t.add_column('Pushed',  style='dim')
        for img in plan.to_delete:
            digest_s = str(img.digest)
            short    = digest_s[:19] if digest_s else '—'
            tag_str  = ', '.join(str(x) for x in img.tags) or '(untagged)'
            size_mb  = f'{img.size_bytes / (1024 * 1024):.1f} MiB' if img.size_bytes else '—'
            t.add_row(short, tag_str, size_mb, str(img.pushed_at) or '—')
        console.print(t)
    console.print(f'[bold]{len(plan.to_delete)} to delete, {plan.kept_count} kept[/bold]; '
                  f'policy: {plan.policy_summary}')
    if dry_run:
        console.print('[dim]Dry-run — no images deleted.[/dim]')
        return
    if not plan.to_delete:
        console.print('Nothing to delete.')
        return
    if not yes and not typer.confirm(
        f'Delete {len(plan.to_delete)} images? This cannot be undone.', default=False):
        console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    digests = [str(img.digest) for img in plan.to_delete if str(img.digest)]
    n       = client.batch_delete_images(repo, digests)
    console.print(f'[green]Deleted[/green] {n} image(s) from {repo}.')


# ── delete ────────────────────────────────────────────────────────────────────

@app.command('delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ecr_delete(ctx           : typer.Context,
               repo          : str  = typer.Argument(..., help='Repository name.'),
               tag_or_digest : str  = typer.Argument(..., help='Image tag or sha256: digest.'),
               yes           : bool = typer.Option(False, '--yes',
                                                   help='Skip confirmation prompt.'),
               as_json       : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete a single ECR image (requires SG_AWS__ECR__ALLOW_MUTATIONS=1)."""
    if not yes and not typer.confirm(
        f'Delete {tag_or_digest!r} from {repo!r}? This cannot be undone.', default=False):
        if as_json:
            typer.echo(json.dumps({'deleted': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client  = ctx.obj['ecr_client']
    deleted = client.delete_image(repo, tag_or_digest)
    if as_json:
        typer.echo(json.dumps({'deleted'      : bool(deleted),
                               'repo'         : repo,
                               'tag_or_digest': tag_or_digest}, indent=2))
        return
    if deleted:
        console.print(f'[green]Deleted[/green] {tag_or_digest} from {repo}.')
    else:
        console.print(f'[yellow]Not found[/yellow] {tag_or_digest} in {repo}.')
        raise typer.Exit(1)


# ── repo-create ───────────────────────────────────────────────────────────────

@app.command('repo-create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ecr_repo_create(ctx     : typer.Context,
                    name    : str  = typer.Argument(..., help='Repository name.'),
                    as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Create an ECR repository (requires SG_AWS__ECR__ALLOW_MUTATIONS=1)."""
    client  = ctx.obj['ecr_client']
    created = client.create_repository(name)
    if as_json:
        typer.echo(json.dumps({'created': bool(created), 'name': name}, indent=2))
        return
    if created:
        console.print(f'[green]Created[/green] repository {name}.')
    else:
        console.print(f'[yellow]Already exists:[/yellow] {name}.')


# ── repo-delete ───────────────────────────────────────────────────────────────

@app.command('repo-delete')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def ecr_repo_delete(ctx     : typer.Context,
                    name    : str  = typer.Argument(..., help='Repository name.'),
                    force   : bool = typer.Option(False, '--force',
                                                  help='Delete even if repository has images.'),
                    yes     : bool = typer.Option(False, '--yes',
                                                  help='Skip confirmation prompt.'),
                    as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Delete an ECR repository (requires SG_AWS__ECR__ALLOW_MUTATIONS=1)."""
    if not yes and not typer.confirm(
        f'Delete repository {name!r}{" (with images)" if force else ""}? This cannot be undone.',
        default=False):
        if as_json:
            typer.echo(json.dumps({'deleted': False, 'aborted': True}, indent=2))
        else:
            console.print('[yellow]Aborted.[/yellow]')
        raise typer.Exit(0)
    client  = ctx.obj['ecr_client']
    deleted = client.delete_repository(name, force=force)
    if as_json:
        typer.echo(json.dumps({'deleted': bool(deleted), 'name': name}, indent=2))
        return
    if deleted:
        console.print(f'[green]Deleted[/green] repository {name}.')
    else:
        console.print(f'[yellow]Not found:[/yellow] {name}.')
        raise typer.Exit(1)
