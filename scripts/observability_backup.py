# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — observability_backup.py
# Backup management sub-app: list, inspect, create, restore, delete, clean.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table   import Table

from scripts.observability_utils import (
    OPENSEARCH_INDEX, BACKUPS_DIR,
    _region, _resolve_stack, _list_stacks, _os_endpoint, _os_resolve,
    _backup_path, _latest_backup,
)
from scripts.observability_opensearch import (
    _scroll_export, _bulk_import,
    _do_import_os_saved_objects, _do_export_os_saved_objects,
    _do_import_grafana, _do_export_grafana,
)

bk_app = typer.Typer(help='Backup management: list, create, restore, delete, and clean. (alias: bk)',
                     no_args_is_help=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _human_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


def _all_backups(stack_filter: Optional[str] = None) -> list:
    """Return metadata dicts for every local backup, newest-first within each stack."""
    out = []
    if not BACKUPS_DIR.exists():
        return out
    for stack_dir in sorted(BACKUPS_DIR.iterdir()):
        if not stack_dir.is_dir():
            continue
        if stack_filter and stack_dir.name != stack_filter:
            continue
        for bk_dir in sorted(stack_dir.iterdir(), reverse=True):
            if not bk_dir.is_dir():
                continue
            manifest = {}
            mf = bk_dir / 'manifest.json'
            if mf.exists():
                try:
                    manifest = json.loads(mf.read_text())
                except Exception:
                    pass
            idx       = manifest.get('index', OPENSEARCH_INDEX)
            data_file = bk_dir / f'{idx}.ndjson'
            dash_file = bk_dir / 'dashboards' / 'opensearch-saved-objects.ndjson'
            graf_dir  = bk_dir / 'dashboards' / 'grafana'
            try:
                size_bytes = sum(f.stat().st_size for f in bk_dir.rglob('*') if f.is_file())
            except Exception:
                size_bytes = 0
            out.append({
                'path'       : bk_dir,
                'stack'      : manifest.get('stack', stack_dir.name),
                'timestamp'  : manifest.get('timestamp', bk_dir.name),
                'region'     : manifest.get('region', '?'),
                'doc_count'  : manifest.get('doc_count', '?'),
                'index'      : idx,
                'has_data'   : data_file.exists(),
                'data_size'  : data_file.stat().st_size if data_file.exists() else 0,
                'has_dash'   : dash_file.exists(),
                'grafana_ct' : len(list(graf_dir.glob('*.json'))) if graf_dir.exists() else 0,
                'size_bytes' : size_bytes,
                'manifest'   : manifest,
            })
    return out


# ── list ───────────────────────────────────────────────────────────────────────

@bk_app.command('list')
def cmd_list(
    stack  : Optional[str] = typer.Argument(None, help='Filter by stack name.'),
    region : Optional[str] = typer.Option(None, '--region'),
):
    """List all local backups (newest first per stack)."""
    c       = Console(highlight=False)
    backups = _all_backups(stack)
    if not backups:
        c.print('\n  [dim]No local backups found.[/]')
        c.print(f'  Backup directory: {BACKUPS_DIR}\n')
        return

    c.print(f'\n  Local backups  ({BACKUPS_DIR})\n')
    tbl = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    tbl.add_column('Stack',     style='bold')
    tbl.add_column('Timestamp')
    tbl.add_column('Docs',      justify='right')
    tbl.add_column('Data',      justify='right')
    tbl.add_column('Dash',      justify='center')
    tbl.add_column('Grafana',   justify='center')
    tbl.add_column('Total',     justify='right')
    tbl.add_column('Region',    style='dim')

    for b in backups:
        tbl.add_row(
            b['stack'],
            b['timestamp'],
            f'{b["doc_count"]:,}' if isinstance(b['doc_count'], int) else str(b['doc_count']),
            _human_size(b['data_size']) if b['has_data'] else '[dim]—[/]',
            '[green]✓[/]' if b['has_dash'] else '[dim]—[/]',
            f'[green]{b["grafana_ct"]}[/]' if b['grafana_ct'] else '[dim]—[/]',
            _human_size(b['size_bytes']),
            b['region'],
        )
    c.print(tbl)
    c.print()


# ── info ───────────────────────────────────────────────────────────────────────

@bk_app.command('info')
def cmd_info(
    path : Optional[str] = typer.Argument(None, help='Backup directory path or timestamp.'),
    stack: Optional[str] = typer.Option(None, '--stack', help='Stack name (needed when using timestamp).'),
):
    """Show detailed contents of a specific backup."""
    c = Console(highlight=False)

    if path and Path(path).exists():
        bk_dir = Path(path)
    elif path and stack:
        bk_dir = BACKUPS_DIR / stack / path
    elif stack:
        bk_dir = _latest_backup(stack)
        if not bk_dir:
            c.print(f'  [red]No backups found for stack {stack!r}[/]')
            raise typer.Exit(1)
    else:
        all_bk = _all_backups()
        if not all_bk:
            c.print('  [red]No local backups found.[/]')
            raise typer.Exit(1)
        bk_dir = all_bk[0]['path']
        c.print(f'  [dim](showing most recent backup — pass a path or --stack to select)[/]')

    if not bk_dir or not bk_dir.exists():
        c.print(f'  [red]Backup not found: {path}[/]')
        raise typer.Exit(1)

    mf = bk_dir / 'manifest.json'
    manifest = json.loads(mf.read_text()) if mf.exists() else {}

    c.print(f'\n  [bold]Backup:[/] {bk_dir}\n')
    c.print(f'    Stack      : {manifest.get("stack", "?")}')
    c.print(f'    Timestamp  : {manifest.get("timestamp", bk_dir.name)}')
    c.print(f'    Region     : {manifest.get("region", "?")}')
    c.print(f'    Documents  : {manifest.get("doc_count", "?"):,}' if isinstance(manifest.get('doc_count'), int)
            else f'    Documents  : {manifest.get("doc_count", "?")}')
    c.print(f'    Index      : {manifest.get("index", OPENSEARCH_INDEX)}')
    c.print(f'    Endpoint   : {manifest.get("opensearch_endpoint", "?")}')
    c.print()

    c.print('  [bold]Files:[/]')
    total = 0
    for f in sorted(bk_dir.rglob('*')):
        if f.is_file():
            sz    = f.stat().st_size
            total += sz
            rel   = f.relative_to(bk_dir)
            c.print(f'    {str(rel):<55}  {_human_size(sz):>8}')
    c.print(f'\n    {"Total":<55}  {_human_size(total):>8}')
    c.print()


# ── create ─────────────────────────────────────────────────────────────────────

@bk_app.command('create')
def cmd_create(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    output_dir  : Optional[str] = typer.Option(None, '--output-dir', '-o'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    index       : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
    admin_user  : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass  : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Full backup: data snapshot + dashboard export into a timestamped directory."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    by_name        = {s['name']: s for s in _list_stacks(r)}
    s              = by_name.get(stack_name, {})
    ts             = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')
    out            = Path(output_dir) if output_dir else BACKUPS_DIR / stack_name / ts
    out.mkdir(parents=True, exist_ok=True)
    auth           = (admin_user, admin_pass) if admin_user else None
    c              = Console(highlight=False)
    c.print(f'\n  [bold]Backup:[/] {stack_name!r}  →  {out}\n')

    ndjson = out / f'{index}.ndjson'
    count  = _scroll_export(ep, r, index, ndjson, c, auth=auth)

    ddir = out / 'dashboards'
    ddir.mkdir(exist_ok=True)
    _do_export_os_saved_objects(ep, r, ddir / 'opensearch-saved-objects.ndjson', c,
                                admin_user=admin_user, admin_pass=admin_pass)
    if grafana_url:
        gdir = ddir / 'grafana'
        gdir.mkdir(exist_ok=True)
        _do_export_grafana(grafana_url, gdir, c)

    manifest = {'stack': stack_name, 'timestamp': ts, 'region': r,
                'index': index, 'doc_count': count,
                'amp_workspace_id': s.get('amp', {}).get('workspaceId') if s.get('amp') else None,
                'opensearch_endpoint': ep}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    c.print(f'\n  [green]✓ Backup complete[/]  {count:,} docs  →  {out}\n')


# ── restore ────────────────────────────────────────────────────────────────────

@bk_app.command('restore')
def cmd_restore(
    name        : Optional[str] = typer.Argument(None, help='Target stack to restore into.'),
    region      : Optional[str] = typer.Option(None, '--region'),
    backup_dir  : Optional[str] = typer.Option(None, '--backup-dir', '-b',
                                               help='Exact backup directory (contains manifest.json).'),
    from_stack  : Optional[str] = typer.Option(None, '--from',
                                               help='Source stack — uses its latest backup.'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    index       : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
    admin_user  : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass  : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Restore data + dashboards from a backup directory into a stack."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    bdir           = (Path(backup_dir) if backup_dir
                      else _latest_backup(from_stack) if from_stack
                      else _latest_backup(stack_name))
    if not bdir or not bdir.exists():
        typer.echo('No backup found. Use --backup-dir or --from <stack>.', err=True)
        raise typer.Exit(1)
    auth     = (admin_user, admin_pass) if admin_user else None
    c        = Console(highlight=False)
    manifest = json.loads((bdir / 'manifest.json').read_text()) if (bdir / 'manifest.json').exists() else {}
    c.print(f'\n  [bold]Restore:[/] {bdir}  →  {stack_name!r}\n')
    if manifest:
        c.print(f'  Source: {manifest.get("stack")} / {manifest.get("timestamp")} / '
                f'{manifest.get("doc_count", "?")} docs\n')

    ndjson = bdir / f'{index}.ndjson'
    if ndjson.exists():
        n = _bulk_import(ep, r, index, ndjson, c, auth=auth)
        c.print(f'  [green]✓ Imported {n:,} documents[/]')
    else:
        c.print(f'  [dim]No data file at {ndjson}[/]')

    saved_obj = bdir / 'dashboards' / 'opensearch-saved-objects.ndjson'
    if saved_obj.exists():
        _do_import_os_saved_objects(ep, r, c, saved_obj,
                                    admin_user=admin_user, admin_pass=admin_pass)

    if grafana_url:
        gdir = bdir / 'dashboards' / 'grafana'
        if gdir.exists():
            for f in gdir.glob('*.json'):
                _do_import_grafana(grafana_url, f, c)

    c.print(f'\n  [green]✓ Restore complete[/]\n')


# ── delete ─────────────────────────────────────────────────────────────────────

@bk_app.command('delete')
def cmd_delete(
    path  : str  = typer.Argument(..., help='Backup directory path to delete.'),
    yes   : bool = typer.Option(False, '--yes', '-y'),
):
    """Permanently delete a specific backup directory."""
    bk_dir = Path(path)
    if not bk_dir.exists():
        typer.echo(f'Path not found: {path}', err=True)
        raise typer.Exit(1)
    if not (bk_dir / 'manifest.json').exists():
        typer.echo(f'No manifest.json in {path} — is this a backup directory?', err=True)
        raise typer.Exit(1)

    c = Console(highlight=False)
    try:
        size = sum(f.stat().st_size for f in bk_dir.rglob('*') if f.is_file())
    except Exception:
        size = 0

    if not yes:
        manifest = {}
        try:
            manifest = json.loads((bk_dir / 'manifest.json').read_text())
        except Exception:
            pass
        c.print(f'\n  Will delete: {bk_dir}')
        c.print(f'  Stack: {manifest.get("stack", "?")}  '
                f'Timestamp: {manifest.get("timestamp", "?")}  '
                f'Size: {_human_size(size)}')
        if not typer.confirm('\n  Confirm permanent deletion?', default=False):
            raise typer.Exit(0)

    shutil.rmtree(bk_dir)
    c.print(f'\n  [green]✓ Deleted[/]  {bk_dir}  ({_human_size(size)} freed)\n')


# ── clean ──────────────────────────────────────────────────────────────────────

@bk_app.command('clean')
def cmd_clean(
    stack : Optional[str] = typer.Argument(None, help='Stack to clean (default: all stacks).'),
    keep  : int           = typer.Option(3, '--keep', '-k',
                                          help='Number of most-recent backups to keep per stack.'),
    yes   : bool          = typer.Option(False, '--yes', '-y'),
):
    """Delete old backups, keeping the N most-recent per stack."""
    c       = Console(highlight=False)
    backups = _all_backups(stack)
    if not backups:
        c.print('\n  [dim]No local backups found.[/]\n')
        return

    # Group by stack, already newest-first within each stack
    by_stack: dict = {}
    for b in backups:
        by_stack.setdefault(b['stack'], []).append(b)

    to_delete = []
    for stk, bks in by_stack.items():
        to_delete.extend(bks[keep:])

    if not to_delete:
        c.print(f'\n  [green]✓ Nothing to clean[/] — each stack has ≤ {keep} backup(s).\n')
        return

    total_size = sum(b['size_bytes'] for b in to_delete)
    c.print(f'\n  Will delete {len(to_delete)} backup(s)  ({_human_size(total_size)} freed)\n')
    for b in to_delete:
        c.print(f'    {b["stack"]}  {b["timestamp"]}  {_human_size(b["size_bytes"])}')
    c.print()

    if not yes:
        if not typer.confirm('  Confirm?', default=False):
            raise typer.Exit(0)

    for b in to_delete:
        shutil.rmtree(b['path'])
        c.print(f'  [green]✓ Deleted[/]  {b["path"]}')

    c.print(f'\n  [green]✓ Cleaned {len(to_delete)} backup(s)[/]  {_human_size(total_size)} freed\n')
