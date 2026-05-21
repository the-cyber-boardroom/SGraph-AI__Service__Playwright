# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__S3
# Typer CLI surface for `sg aws s3 *` commands.
#
# Command tree:
#   sg aws s3 ls          [s3://bucket[/prefix]] [--recursive] [--json]
#   sg aws s3 view        <s3://bucket/key>       [--raw] [--json]
#   sg aws s3 cat         <s3://bucket/key>
#   sg aws s3 tail        <s3://bucket/key>       [--since DUR] [--lines N] [--follow]
#   sg aws s3 head        <s3://bucket/key>       [--lines N]
#   sg aws s3 stat        <s3://bucket/key>       [--json]
#   sg aws s3 presign     <s3://bucket/key>       [--ttl SEC]
#   sg aws s3 search      <s3://bucket/prefix>    --pattern TEXT [--json]
#   sg aws s3 cp          <src> <dst>             [--yes]
#   sg aws s3 mv          <src> <dst>             [--yes]
#   sg aws s3 rm          <s3://bucket/key>       [--yes]
#   sg aws s3 sync        <local-dir> <s3://..>   [--dry-run] [--yes]
#   sg aws s3 edit        <s3://bucket/key>       [--editor EDITOR] [--keep-local]
#   sg aws s3 bucket-list [--json]
#   sg aws s3 bucket-stat <bucket>                [--json]
#   sg aws s3 bucket-create <bucket>              [--region R] [--yes]
#
# Read-only commands always allowed.
# Mutations require SG_AWS__S3__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
import json
import os
import sys

import typer
from rich.console import Console
from rich.panel   import Panel
from rich.syntax  import Syntax
from rich.table   import Table

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm                      import confirm_or_abort
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate                    import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.s3.enums.Enum__S3__Object__Format         import Enum__S3__Object__Format
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client                import S3__AWS__Client
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Format__Detector           import S3__Format__Detector
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Source__Adapter            import S3__Source__Adapter
from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Vim__Editor                import S3__Vim__Editor
from sg_compute.cli.base.Spec__CLI__Errors                                  import spec_cli_errors

app     = typer.Typer(name='s3', help='S3 object and bucket management.', no_args_is_help=True)
console = Console()

_MUTATION_ENV = 'SG_AWS__S3__ALLOW_MUTATIONS'


def _client() -> S3__AWS__Client:
    return S3__AWS__Client()


@app.command('browse', help='Interactive S3 bucket/folder/file browser + viewer (Textual). No-TTY prints a listing.')
def browse(path: str = typer.Argument('', help='Optional s3://bucket/prefix to start at')):
    from sgraph_ai_service_playwright__cli.aws.s3.tui.cli.Cli__S3__Browser import run_browse  # lazy — textual not required to register the CLI
    run_browse(path)


def _parse_s3_uri(uri: str):                                                      # returns (bucket, key) tuple
    if not uri.startswith('s3://'):
        return '', uri
    rest   = uri[5:]
    idx    = rest.find('/')
    if idx == -1:
        return rest, ''
    return rest[:idx], rest[idx + 1:]


def _fmt_bytes(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} PB'


# ── ls ────────────────────────────────────────────────────────────────────────

@app.command('ls')
@spec_cli_errors
def cmd_ls(path      : str  = typer.Argument('', help='s3://bucket[/prefix] or empty to list all buckets.'),
           recursive : bool = typer.Option(False, '--recursive', '-r', help='List all objects recursively.'),
           as_json   : bool = typer.Option(False, '--json',            help='Output as JSON.')):
    """List S3 buckets or objects within a bucket/prefix."""
    client = _client()
    if not path or path == 's3://':                                               # list all buckets
        buckets = client.list_buckets()
        if as_json:
            typer.echo(json.dumps([{'name': str(b.name), 'created': b.creation_date}
                                    for b in buckets], indent=2))
            return
        t = Table(title='S3 Buckets')
        t.add_column('Bucket',  style='cyan')
        t.add_column('Created', style='dim')
        for b in buckets:
            t.add_row(str(b.name), b.creation_date[:10] if b.creation_date else '—')
        console.print(t)
        return

    bucket, prefix = _parse_s3_uri(path)
    if not bucket:
        console.print('[red]Invalid S3 path.[/red]')
        raise typer.Exit(1)

    resp = client.list_objects(bucket, prefix, recursive=recursive)
    if as_json:
        typer.echo(json.dumps({
            'bucket'  : str(resp.bucket),
            'prefix'  : resp.prefix,
            'objects' : [{'key': str(o.key), 'size': o.size,
                          'last_modified': o.last_modified,
                          'etag': str(o.etag)} for o in resp.objects],
            'prefixes': resp.prefixes,
        }, indent=2))
        return

    if not resp.objects and not resp.prefixes:
        console.print('No objects found.')
        return

    t = Table()
    t.add_column('Key',           style='cyan')
    t.add_column('Size',          style='green',  justify='right')
    t.add_column('Last Modified', style='dim')
    for pf in resp.prefixes:
        t.add_row(f'[dim]{pf}[/dim]', '', '')
    for obj in resp.objects:
        t.add_row(str(obj.key), _fmt_bytes(obj.size),
                  obj.last_modified[:19] if obj.last_modified else '—')
    console.print(t)


# ── stat ──────────────────────────────────────────────────────────────────────

@app.command('stat')
@spec_cli_errors
def cmd_stat(path    : str  = typer.Argument(..., help='s3://bucket/key'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show S3 object metadata (size, ETag, storage class, encryption)."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    stat = _client().head_object(bucket, key)
    if stat is None:
        console.print(f'[red]Object not found:[/red] {path}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps({
            'bucket'       : str(stat.bucket),
            'key'          : str(stat.key),
            'size'         : stat.size,
            'last_modified': stat.last_modified,
            'etag'         : str(stat.etag),
            'storage_class': str(stat.storage_class),
            'content_type' : stat.content_type,
            'encryption'   : stat.encryption,
            'version_id'   : stat.version_id,
        }, indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16)
    t.add_column()
    t.add_row('bucket',        str(stat.bucket))
    t.add_row('key',           str(stat.key))
    t.add_row('size',          _fmt_bytes(stat.size))
    t.add_row('last_modified', stat.last_modified or '—')
    t.add_row('etag',          str(stat.etag))
    t.add_row('storage_class', str(stat.storage_class))
    t.add_row('content_type',  stat.content_type  or '—')
    t.add_row('encryption',    stat.encryption    or '—')
    t.add_row('version_id',    stat.version_id    or '—')
    console.print()
    console.print(t)
    console.print()


# ── view ──────────────────────────────────────────────────────────────────────

@app.command('view')
@spec_cli_errors
def cmd_view(path    : str  = typer.Argument(..., help='s3://bucket/key'),
             raw     : bool = typer.Option(False, '--raw',  help='Skip format detection; print raw bytes.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON (JSON objects only).')):
    """View object content with format-aware rendering."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    client  = _client()
    data    = client.get_object_body(bucket, key)
    if not data:
        console.print('[red]Empty or inaccessible object.[/red]')
        raise typer.Exit(1)

    header  = data[:512]
    fmt     = S3__Format__Detector().detect(key, header, raw=raw)

    if fmt == Enum__S3__Object__Format.GZIP:
        try:
            data = gzip.decompress(data)
            fmt  = S3__Format__Detector().detect(key.replace('.gz', ''), data[:512])
        except Exception:
            pass

    if fmt == Enum__S3__Object__Format.BINARY:
        stat = client.head_object(bucket, key)
        sz   = stat.size if stat else len(data)
        console.print(Panel(f'Binary object — {_fmt_bytes(sz)}\nUse --raw to force text output.',
                            title=key))
        return

    text = data.decode('utf-8', errors='replace')

    if fmt == Enum__S3__Object__Format.JSON:
        try:
            parsed = json.loads(text)
            if as_json:
                typer.echo(json.dumps(parsed, indent=2))
            else:
                console.print(Syntax(json.dumps(parsed, indent=2), 'json', theme='monokai'))
        except json.JSONDecodeError:
            console.print(text)
        return

    if fmt == Enum__S3__Object__Format.YAML:
        console.print(Syntax(text, 'yaml', theme='monokai'))
        return

    if fmt == Enum__S3__Object__Format.MARKDOWN:
        console.print(text)
        return

    if fmt == Enum__S3__Object__Format.CSV:
        lines = text.splitlines()
        if lines:
            t = Table()
            headers = lines[0].split(',')
            for h in headers:
                t.add_column(h.strip(), style='cyan')
            for row in lines[1:20]:                                               # show first 20 data rows
                t.add_row(*[c.strip() for c in row.split(',')[:len(headers)]])
            console.print(t)
            if len(lines) > 21:
                console.print(f'[dim]… {len(lines)-21} more rows[/dim]')
        return

    console.print(text)


# ── cat ───────────────────────────────────────────────────────────────────────

@app.command('cat')
@spec_cli_errors
def cmd_cat(path : str = typer.Argument(..., help='s3://bucket/key')):
    """Stream object content to stdout."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    for chunk in _client().stream_object(bucket, key):
        sys.stdout.buffer.write(chunk)
    sys.stdout.buffer.flush()


# ── head ──────────────────────────────────────────────────────────────────────

@app.command('head')
@spec_cli_errors
def cmd_head(path  : str = typer.Argument(..., help='s3://bucket/key'),
             lines : int = typer.Option(10, '--lines', '-n', help='Number of lines to show.')):
    """Print the first N lines of an object."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    data = _client().get_object_body(bucket, key)
    text = data.decode('utf-8', errors='replace')
    for line in text.splitlines()[:lines]:
        typer.echo(line)


# ── tail ──────────────────────────────────────────────────────────────────────

@app.command('tail')
@spec_cli_errors
def cmd_tail(path   : str  = typer.Argument(..., help='s3://bucket/key'),
             lines  : int  = typer.Option(100,  '--lines',  '-n',      help='Number of tail lines.'),
             since  : str  = typer.Option('',   '--since',  '-s',      help='Duration string e.g. 5m, 1h.'),
             follow : bool = typer.Option(False, '--follow', '-f',      help='Poll for new lines.')):
    """Print the last N lines of an object; optionally follow for new appended lines."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    data     = _client().get_object_body(bucket, key)
    text     = data.decode('utf-8', errors='replace')
    all_lines = text.splitlines()
    for line in all_lines[-lines:]:
        typer.echo(line)
    if follow:
        adapter = S3__Source__Adapter(s3_client=_client())
        stream_id = f'{bucket}/{key}'
        try:
            for event in adapter.tail(stream_id, since):
                typer.echo(event.message)
        except KeyboardInterrupt:
            pass


# ── presign ───────────────────────────────────────────────────────────────────

@app.command('presign')
@spec_cli_errors
def cmd_presign(path : str = typer.Argument(..., help='s3://bucket/key'),
                ttl  : int = typer.Option(3600, '--ttl', help='Expiry in seconds (max 604800 = 7 days).')):
    """Generate a presigned download URL for an S3 object."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    cap = 604800                                                                   # 7 days max
    ttl = min(ttl, cap)
    url = _client().generate_presigned_url(bucket, key, ttl_seconds=ttl)
    if not url:
        console.print('[red]Failed to generate presigned URL.[/red]')
        raise typer.Exit(1)
    typer.echo(url)


# ── search ────────────────────────────────────────────────────────────────────

@app.command('search')
@spec_cli_errors
def cmd_search(path    : str  = typer.Argument(..., help='s3://bucket/prefix'),
               pattern : str  = typer.Option(..., '--pattern', '-p', help='Key pattern (glob or substring).'),
               as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Search for objects whose keys match a pattern."""
    bucket, prefix = _parse_s3_uri(path)
    if not bucket:
        bucket = path
        prefix = ''
    matches = _client().search_objects(bucket, prefix, pattern)
    if as_json:
        typer.echo(json.dumps([{'key': str(o.key), 'size': o.size,
                                 'last_modified': o.last_modified}
                                for o in matches], indent=2))
        return
    if not matches:
        console.print('No matching objects.')
        return
    t = Table()
    t.add_column('Key',  style='cyan')
    t.add_column('Size', style='green', justify='right')
    for obj in matches:
        t.add_row(str(obj.key), _fmt_bytes(obj.size))
    console.print(t)


# ── bucket-list ───────────────────────────────────────────────────────────────

@app.command('bucket-list')
@spec_cli_errors
def cmd_bucket_list(as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List all S3 buckets in the account."""
    buckets = _client().list_buckets()
    if as_json:
        typer.echo(json.dumps([{'name': str(b.name), 'created': b.creation_date}
                                for b in buckets], indent=2))
        return
    if not buckets:
        console.print('No buckets found.')
        return
    t = Table(title='S3 Buckets')
    t.add_column('Bucket',  style='cyan')
    t.add_column('Created', style='dim')
    for b in buckets:
        t.add_row(str(b.name), b.creation_date[:10] if b.creation_date else '—')
    console.print(t)


# ── bucket-stat ───────────────────────────────────────────────────────────────

@app.command('bucket-stat')
@spec_cli_errors
def cmd_bucket_stat(bucket  : str  = typer.Argument(..., help='Bucket name.'),
                    as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show bucket metadata: region, versioning, estimated size."""
    client     = _client()
    region     = client.get_bucket_region(bucket)
    versioning = client.get_bucket_versioning(bucket)
    size_info  = client.get_bucket_size_estimate(bucket)
    if as_json:
        typer.echo(json.dumps({
            'bucket'      : bucket,
            'region'      : region,
            'versioning'  : versioning,
            'object_count': size_info.get('object_count', 0),
            'total_bytes' : size_info.get('total_bytes', 0),
        }, indent=2))
        return
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16)
    t.add_column()
    t.add_row('bucket',       bucket)
    t.add_row('region',       region       or '—')
    t.add_row('versioning',   versioning   or 'Disabled')
    t.add_row('object count', str(size_info.get('object_count', 0)))
    t.add_row('total size',   _fmt_bytes(size_info.get('total_bytes', 0)))
    console.print()
    console.print(t)
    console.print()


# ── cp ────────────────────────────────────────────────────────────────────────

@app.command('cp')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def cmd_cp(src     : str  = typer.Argument(..., help='Source — local path or s3://bucket/key.'),
           dst     : str  = typer.Argument(..., help='Destination — s3://bucket/key or local path.'),
           yes     : bool = typer.Option(False, '--yes', '-y',   help='Skip confirmation prompt.'),
           dry_run : bool = typer.Option(False, '--dry-run',     help='Print action without executing.')):
    """Copy an object from src to dst. Either side may be local or s3://."""
    if not confirm_or_abort(f'Copy {src} → {dst}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    client    = _client()
    src_local = not src.startswith('s3://')
    dst_local = not dst.startswith('s3://')

    if src_local and not dst_local:                                               # local → s3
        dst_bucket, dst_key = _parse_s3_uri(dst)
        if not dst_bucket or not dst_key:
            console.print('[red]Invalid destination S3 path.[/red]')
            raise typer.Exit(1)
        with open(src, 'rb') as fh:
            body = fh.read()
        client.put_object(dst_bucket, dst_key, body)
    elif not src_local and dst_local:                                             # s3 → local
        src_bucket, src_key = _parse_s3_uri(src)
        body = client.get_object_body(src_bucket, src_key)
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        with open(dst, 'wb') as fh:
            fh.write(body)
    elif not src_local and not dst_local:                                         # s3 → s3
        sb, sk = _parse_s3_uri(src)
        db, dk = _parse_s3_uri(dst)
        client.copy_object(sb, sk, db, dk)
    else:
        console.print('[red]At least one side must be an S3 path.[/red]')
        raise typer.Exit(1)

    console.print(f'[green]Copied[/green] {src} → {dst}')


# ── mv ────────────────────────────────────────────────────────────────────────

@app.command('mv')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def cmd_mv(src     : str  = typer.Argument(..., help='Source s3://bucket/key.'),
           dst     : str  = typer.Argument(..., help='Destination s3://bucket/key.'),
           yes     : bool = typer.Option(False, '--yes', '-y',   help='Skip confirmation prompt.'),
           dry_run : bool = typer.Option(False, '--dry-run',     help='Print action without executing.')):
    """Move an S3 object (copy + delete)."""
    if not confirm_or_abort(f'Move {src} → {dst}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    client = _client()
    sb, sk = _parse_s3_uri(src)
    db, dk = _parse_s3_uri(dst)
    if not sb or not sk or not db or not dk:
        console.print('[red]Both src and dst must be full s3://bucket/key paths for mv.[/red]')
        raise typer.Exit(1)
    client.copy_object(sb, sk, db, dk)
    client.delete_object(sb, sk)
    console.print(f'[green]Moved[/green] {src} → {dst}')


# ── rm ────────────────────────────────────────────────────────────────────────

@app.command('rm')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def cmd_rm(path    : str  = typer.Argument(..., help='s3://bucket/key'),
           yes     : bool = typer.Option(False, '--yes', '-y',   help='Skip confirmation prompt.'),
           dry_run : bool = typer.Option(False, '--dry-run',     help='Print action without executing.')):
    """Delete an S3 object."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    if not confirm_or_abort(f'Delete {path}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    _client().delete_object(bucket, key)
    console.print(f'[green]Deleted[/green] {path}')


# ── sync ──────────────────────────────────────────────────────────────────────

@app.command('sync')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def cmd_sync(local_dir : str  = typer.Argument(..., help='Local directory.'),
             s3_path   : str  = typer.Argument(..., help='s3://bucket/prefix destination.'),
             dry_run   : bool = typer.Option(False, '--dry-run', help='Print what would be uploaded without doing it.'),
             yes       : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.')):
    """Sync a local directory to an S3 prefix (local → S3 only)."""
    bucket, prefix = _parse_s3_uri(s3_path)
    if not bucket:
        console.print('[red]Destination must be an s3:// path.[/red]')
        raise typer.Exit(1)
    if not os.path.isdir(local_dir):
        console.print(f'[red]Local directory not found:[/red] {local_dir}')
        raise typer.Exit(1)

    to_upload = []
    for root, _, files in os.walk(local_dir):
        for fname in files:
            local_path  = os.path.join(root, fname)
            rel         = os.path.relpath(local_path, local_dir)
            remote_key  = (prefix.rstrip('/') + '/' + rel).lstrip('/')
            to_upload.append((local_path, remote_key))

    if not to_upload:
        console.print('Nothing to sync.')
        return

    console.print(f'[bold]Syncing {len(to_upload)} file(s) → s3://{bucket}/{prefix}[/bold]')
    for local_path, remote_key in to_upload:
        console.print(f'  {"(dry-run) " if dry_run else ""}upload: {remote_key}')

    if dry_run:
        return

    if not confirm_or_abort(f'Upload {len(to_upload)} files?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)

    client  = _client()
    for local_path, remote_key in to_upload:
        with open(local_path, 'rb') as fh:
            body = fh.read()
        client.put_object(bucket, remote_key, body)
    console.print(f'[green]Uploaded {len(to_upload)}/{len(to_upload)} files.[/green]')


# ── edit ──────────────────────────────────────────────────────────────────────

@app.command('edit')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def cmd_edit(path       : str  = typer.Argument(..., help='s3://bucket/key'),
             editor     : str  = typer.Option('',   '--editor', help='Editor binary (default $EDITOR or vim).'),
             keep_local : bool = typer.Option(False, '--keep-local', help='Keep temp file after editing.')):
    """Open an S3 object in $EDITOR; upload on save if unchanged ETag."""
    bucket, key = _parse_s3_uri(path)
    if not bucket or not key:
        console.print('[red]Specify a full s3://bucket/key path.[/red]')
        raise typer.Exit(1)
    vim_editor = S3__Vim__Editor(
        s3_client  = _client(),
        keep_local = keep_local,
        editor     = editor,
    )
    result = vim_editor.edit(bucket, key)
    reason = result.get('reason', '')
    if result.get('ok'):
        if reason == 'no_change':
            console.print('[dim]No change — skipping upload.[/dim]')
        else:
            console.print(f'[green]Uploaded[/green] {path}')
    else:
        if reason == 'etag_conflict':
            console.print('[red]ETag conflict — remote was modified while editing.[/red]')
            console.print(f'  Your edits saved to: {result.get("conflict_file", "")}')
        elif reason == 'object_not_found':
            console.print(f'[red]Object not found:[/red] {path}')
        else:
            console.print(f'[red]Edit failed:[/red] {reason}')
        raise typer.Exit(1)


# ── bucket-create ─────────────────────────────────────────────────────────────

@app.command('bucket-create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
def cmd_bucket_create(bucket  : str  = typer.Argument(..., help='Bucket name to create.'),
                      region  : str  = typer.Option('',    '--region', '-r', help='AWS region.'),
                      yes     : bool = typer.Option(False, '--yes',    '-y', help='Skip confirmation.'),
                      dry_run : bool = typer.Option(False, '--dry-run',      help='Print action without executing.')):
    """Create an S3 bucket with versioning enabled and public access blocked."""
    if not confirm_or_abort(f'Create bucket "{bucket}"?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    _client().create_bucket(bucket, region=region)
    console.print(f'[green]Created[/green] {bucket}')
