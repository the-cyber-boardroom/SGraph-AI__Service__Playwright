# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — observability_opensearch.py
# OpenSearch index, index-pattern, and dashboard management sub-app.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time
from pathlib import Path
from typing import Optional

import requests
import typer
from rich.console import Console
from rich.table   import Table

from scripts.observability_utils import (
    OPENSEARCH_INDEX, DASHBOARDS_DIR, BACKUPS_DIR, SCROLL_TTL, SCROLL_SIZE, BULK_CHUNK,
    _region, _sigv4, _os_req, _os_resolve, _backup_path, _latest_backup,
)

os_app = typer.Typer(help='OpenSearch index, index-pattern, and dashboard management. (alias: os)',
                     no_args_is_help=True)

# ── Dashboard helpers ──────────────────────────────────────────────────────────

def _verify_index_pattern_exists(base: str, hdrs: dict, auth,
                                  pattern_id: str = OPENSEARCH_INDEX) -> bool:
    r = requests.get(f'{base}/api/saved_objects/index-pattern/{pattern_id}',
                     headers=hdrs, auth=auth, timeout=15)
    if r.status_code >= 300:
        return False
    try:
        return r.json().get('attributes', {}).get('title') == pattern_id
    except (ValueError, AttributeError):
        return False


def _do_import_os_saved_objects(endpoint: str, region: str, c: Console,
                                 ndjson_path: Optional[Path] = None,
                                 admin_user: str = '', admin_pass: str = ''):
    auth = (admin_user, admin_pass)
    hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true', 'securitytenant': 'global'}
    base = f'https://{endpoint}/_dashboards'

    # Body: title + timeFieldName only — 'fields' key causes AOS 400.
    # URL:  tenant via header only — &security_tenant= in query string also causes 400.
    ip_body = {'attributes': {'title': OPENSEARCH_INDEX, 'timeFieldName': '@timestamp'}}
    url     = f'{base}/api/saved_objects/index-pattern/{OPENSEARCH_INDEX}?overwrite=true'
    resp    = requests.post(url, data=json.dumps(ip_body), headers=hdrs, auth=auth, timeout=30)
    c.print(f'  [dim]  POST index-pattern: HTTP {resp.status_code}[/]')

    dv_ok = _verify_index_pattern_exists(base, hdrs, auth)
    if dv_ok:
        c.print(f'  [green]✓ Index pattern created[/]  ({OPENSEARCH_INDEX})')
    else:
        c.print(f'  [red]✗ Index pattern creation failed (HTTP {resp.status_code})[/]')
        c.print(f'    Response: {resp.text[:400]}')
        c.print(f'    Check admin credentials and that the domain has FGAC enabled.')

    src = ndjson_path or (DASHBOARDS_DIR / 'opensearch-instance-lifecycle.ndjson')
    if not src.exists():
        return dv_ok

    _TOP_STRIP  = {'version', 'updated_at', 'migrationVersion'}
    _ATTR_STRIP = {'version', 'uiStateJSON', 'hits'}
    objects = []
    for raw in src.read_bytes().splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if obj.get('type') == 'index-pattern':
            continue
        for f in _TOP_STRIP:
            obj.pop(f, None)
        attrs = obj.get('attributes', {})
        for f in _ATTR_STRIP:
            attrs.pop(f, None)
        objects.append({'type': obj.get('type'), 'id': obj.get('id'),
                        'attributes': attrs, 'references': obj.get('references', [])})

    if not objects:
        return dv_ok

    bulk_url  = f'{base}/api/saved_objects/_bulk_create?overwrite=true'
    bulk_resp = requests.post(bulk_url, json=objects, headers=hdrs, auth=auth, timeout=30)
    c.print(f'  [dim]  _bulk_create: HTTP {bulk_resp.status_code}[/]')

    if bulk_resp.status_code < 300:
        saved    = bulk_resp.json().get('saved_objects', [])
        bulk_ok  = [o for o in saved if 'error' not in o]
        bulk_err = [o for o in saved if 'error'     in o]
        if bulk_ok:
            c.print(f'  [green]✓ {len(bulk_ok)} visualizations/dashboards imported[/]')
        if bulk_err:
            c.print(f'  [yellow]⚠ {len(bulk_err)} objects had errors:[/]')
            for e in bulk_err[:5]:
                c.print(f'    {e.get("type")} {e.get("id")}: '
                        f'{e.get("error", {}).get("message", "?")}')
        return dv_ok

    c.print(f'  [red]✗ bulk_create failed: HTTP {bulk_resp.status_code}[/]')
    c.print(f'    {bulk_resp.text[:400]}')
    c.print(f'    Import manually: OS Dashboards → Stack Management → Saved Objects → Import')
    c.print(f'    File: {DASHBOARDS_DIR / "opensearch-instance-lifecycle.ndjson"}')
    return dv_ok


def _do_export_os_saved_objects(endpoint: str, region: str, output: Path, c: Console,
                                 admin_user: str = '', admin_pass: str = ''):
    url  = f'https://{endpoint}/_dashboards/api/saved_objects/_export'
    body = json.dumps({'type': ['index-pattern', 'visualization', 'dashboard'],
                       'includeReferencesDeep': True}).encode()
    auth = (admin_user, admin_pass) if admin_user else None
    hdrs = {'osd-xsrf': 'true'}
    if auth:
        resp = requests.post(url, data=body,
                             headers={'Content-Type': 'application/json', **hdrs},
                             auth=auth, timeout=60)
    else:
        resp = _sigv4('POST', url, region, body, hdrs)
    if resp.status_code < 300:
        output.write_bytes(resp.content)
        c.print(f'  [green]✓ OS saved objects exported[/]  ({len(resp.content):,} bytes → {output.name})')
    else:
        c.print(f'  [red]✗ OS export HTTP {resp.status_code}:[/] {resp.text[:200]}')


def _do_import_grafana(workspace_url: str, dash_path: Path, c: Console,
                        amp_ds: str = 'grafana-amazonprometheus-datasource'):
    import boto3 as _boto3
    url      = workspace_url.rstrip('/')
    host     = url.removeprefix('https://').removeprefix('http://')
    ws_id    = host.split('.')[0]
    grafana  = _boto3.client('grafana', region_name=_region())
    key_name = f'sg-import-{int(time.time())}'
    api_key  = grafana.create_workspace_api_key(
        keyName=key_name, keyRole='ADMIN', secondsToLive=300, workspaceId=ws_id)['key']
    try:
        payload = {'dashboard': json.loads(dash_path.read_text()), 'overwrite': True,
                   'inputs': [{'name': 'DS_AMP', 'type': 'datasource',
                               'pluginId': 'grafana-amazonprometheus-datasource',
                               'value': amp_ds}]}
        r = requests.post(f'{url}/api/dashboards/import',
                          headers={'Authorization': f'Bearer {api_key}',
                                   'Content-Type': 'application/json'},
                          json=payload, timeout=30)
        if r.status_code < 300:
            c.print(f'  [green]✓ Grafana dashboard imported[/]  ({dash_path.name})')
        else:
            c.print(f'  [red]✗ Grafana import HTTP {r.status_code}:[/] {r.text[:200]}')
    finally:
        try:
            grafana.delete_workspace_api_key(keyName=key_name, workspaceId=ws_id)
        except Exception:
            pass  # import cleanup


def _do_export_grafana(workspace_url: str, output_dir: Path, c: Console):
    import boto3 as _boto3
    url      = workspace_url.rstrip('/')
    host     = url.removeprefix('https://').removeprefix('http://')
    ws_id    = host.split('.')[0]
    grafana  = _boto3.client('grafana', region_name=_region())
    key_name = f'sg-export-{int(time.time())}'
    api_key  = grafana.create_workspace_api_key(
        keyName=key_name, keyRole='VIEWER', secondsToLive=300, workspaceId=ws_id)['key']
    hdrs     = {'Authorization': f'Bearer {api_key}'}
    try:
        search = requests.get(f'{url}/api/search?type=dash-db', headers=hdrs, timeout=30)
        if search.status_code != 200:
            c.print(f'  [red]✗ Grafana search HTTP {search.status_code}[/]')
            return
        for dash in search.json():
            uid  = dash.get('uid')
            slug = dash.get('uri', '').replace('db/', '') or uid
            dr   = requests.get(f'{url}/api/dashboards/uid/{uid}', headers=hdrs, timeout=30)
            if dr.status_code == 200:
                fname = output_dir / f'{slug}.json'
                fname.write_text(json.dumps(dr.json(), indent=2))
                c.print(f'  [green]✓ Grafana exported[/]  {slug}')
    finally:
        try:
            grafana.delete_workspace_api_key(keyName=key_name, workspaceId=ws_id)
        except Exception:
            pass  # export cleanup


def _check_os_dashboards(endpoint: str, region: str, c: Console,
                          admin_user: str = '', admin_pass: str = '') -> bool:
    auth = (admin_user, admin_pass) if admin_user else None
    base = f'https://{endpoint}/_dashboards'
    c.print(f'\n  [bold]OpenSearch Dashboards health check[/]\n')

    found_tenants = []
    for tenant in ('global', 'private', '__user__'):
        hdrs     = {'Content-Type': 'application/json', 'osd-xsrf': 'true',
                    'securitytenant': tenant}
        patterns = []
        for path in ('/api/saved_objects/_find?type=index-pattern&per_page=100',
                     '/api/saved_objects/_find?type=data-view&per_page=100',
                     '/api/data_views/data_view'):
            try:
                resp = requests.get(f'{base}{path}', headers=hdrs, auth=auth, timeout=15)
            except Exception:
                continue
            if resp.status_code >= 300:
                continue
            data = resp.json()
            for p in data.get('saved_objects', data.get('data_views', [])):
                title = (p.get('attributes', {}).get('title')
                         or p.get('title') or p.get('id', ''))
                if title:
                    patterns.append(title)
            if patterns:
                break
        has_target = any(OPENSEARCH_INDEX in p for p in patterns)
        icon        = '[green]✓[/]' if has_target else '[yellow]—[/]'
        c.print(f'    {icon}  tenant=[bold]{tenant}[/]  index-patterns: '
                f'{patterns or "(none)"}')
        if has_target:
            found_tenants.append(tenant)

    hdrs_global = {'Content-Type': 'application/json', 'osd-xsrf': 'true',
                   'securitytenant': 'global'}
    for obj_type in ('dashboard', 'visualization'):
        try:
            resp = requests.get(f'{base}/api/saved_objects/_find?type={obj_type}&per_page=100',
                                headers=hdrs_global, auth=auth, timeout=15)
        except Exception:
            continue
        if resp.status_code < 300:
            objs  = resp.json().get('saved_objects', [])
            names = [o.get('attributes', {}).get('title', o.get('id', '?')) for o in objs]
            icon  = '[green]✓[/]' if names else '[yellow]—[/]'
            c.print(f'    {icon}  {obj_type}s (global):  {names or "(none)"}')

    doc_id    = f'index-pattern:{OPENSEARCH_INDEX}'
    sys_found = False
    for idx in ('.opensearch_dashboards', '.opensearch_dashboards_1', '.kibana', '.kibana_1'):
        try:
            resp = _sigv4('GET', f'https://{endpoint}/{idx}/_doc/{doc_id}', region)
        except Exception:
            continue
        if resp.status_code == 200:
            c.print(f'    [green]✓[/]  system index [dim]{idx}[/]:  doc found (id={doc_id!r})')
            sys_found = True
            break
        if resp.status_code == 404:
            c.print(f'    [yellow]—[/]  system index [dim]{idx}[/]:  doc not found')
            break

    if sys_found and not found_tenants:
        c.print(f'\n  [yellow]⚠ Index pattern exists in the system index but is not '
                f'visible via any Dashboards tenant.[/]')
        c.print(f'    Try: OS Dashboards → top-right avatar → Switch tenants → Global')
    elif found_tenants and 'global' not in found_tenants:
        c.print(f'\n  [yellow]⚠ Index pattern is in tenant(s) {found_tenants} but NOT '
                f'in [bold]global[/].[/]')
        c.print(f'    Switch to that tenant in the Dashboards UI to see it.')
    elif 'global' in found_tenants:
        c.print(f'\n  [green]✓ Index pattern visible in global tenant — '
                f'switch to Global in the Dashboards UI if you do not see it.[/]')

    c.print()
    return bool(found_tenants or sys_found)


# ── Scroll / bulk helpers ──────────────────────────────────────────────────────

def _scroll_export(endpoint: str, region: str, index: str,
                   output: Path, c: Console, auth=None) -> int:
    url  = f'https://{endpoint}/{index}/_search?scroll={SCROLL_TTL}'
    body = json.dumps({'size': SCROLL_SIZE, 'query': {'match_all': {}},
                       'sort': ['_doc']}).encode()
    resp = _os_req('POST', url, region, body, auth)
    if resp.status_code != 200:
        c.print(f'  [red]✗ Scroll init HTTP {resp.status_code}:[/] {resp.text[:200]}')
        return 0
    data      = resp.json()
    scroll_id = data['_scroll_id']
    total_raw = data['hits']['total']
    total     = total_raw['value'] if isinstance(total_raw, dict) else total_raw
    c.print(f'  Total documents: {total:,}')
    count     = 0
    with output.open('w') as fh:
        while True:
            hits = data['hits']['hits']
            if not hits:
                break
            for hit in hits:
                fh.write(json.dumps(hit['_source']) + '\n')
                count += 1
            if count % 5000 == 0:
                c.print(f'  [dim]  {count:,} / {total:,} exported…[/]')
            scroll_resp = _os_req('POST', f'https://{endpoint}/_search/scroll', region,
                                   json.dumps({'scroll': SCROLL_TTL,
                                               'scroll_id': scroll_id}).encode(), auth)
            if scroll_resp.status_code != 200:
                break
            data      = scroll_resp.json()
            scroll_id = data.get('_scroll_id', scroll_id)
    _os_req('DELETE', f'https://{endpoint}/_search/scroll', region,
            json.dumps({'scroll_id': scroll_id}).encode(), auth)
    return count


def _bulk_import(endpoint: str, region: str, index: str,
                 src: Path, c: Console, auth=None) -> int:
    lines = [ln for ln in src.read_text().splitlines() if ln.strip()]
    c.print(f'  Documents to import: {len(lines):,}')
    count = 0
    for i in range(0, len(lines), BULK_CHUNK):
        chunk = lines[i:i + BULK_CHUNK]
        body  = ''
        for line in chunk:
            body  += json.dumps({'index': {'_index': index}}) + '\n' + line + '\n'
            count += 1
        resp = _os_req('POST', f'https://{endpoint}/_bulk', region, body.encode(),
                       auth, {'Content-Type': 'application/x-ndjson'})
        if resp.status_code >= 300:
            c.print(f'  [red]✗ Bulk HTTP {resp.status_code}:[/] {resp.text[:200]}')
            break
        errs = [it for it in resp.json().get('items', [])
                if it.get('index', {}).get('error')]
        if errs:
            c.print(f'  [yellow]⚠ {len(errs)} bulk errors in chunk[/]')
        if count % 5000 < BULK_CHUNK:
            c.print(f'  [dim]  {count:,} / {len(lines):,} imported…[/]')
    return count


# ── dashboard-import ───────────────────────────────────────────────────────────

@os_app.command('dashboard-import')
def cmd_dashboard_import(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    amp_ds      : str           = typer.Option('grafana-amazonprometheus-datasource', '--amp-datasource'),
    admin_user  : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass  : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Import OpenSearch saved objects + Grafana dashboard from library/docs/ops/dashboards/."""
    if not admin_user or not admin_pass:
        typer.echo(
            '\nError: admin credentials required.\n'
            '  export OB_OS_ADMIN_USER=admin\n'
            '  export OB_OS_ADMIN_PASS="<master-password>"\n'
            '\nThe master password was set when the OpenSearch domain was created.\n'
            'Retrieve it from AWS Secrets Manager if you do not have it locally.\n',
            err=True)
        raise typer.Exit(1)
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    c              = Console(highlight=False)
    c.print(f'\n  Importing dashboards → [bold]{stack_name}[/]\n')
    _do_import_os_saved_objects(ep, r, c, admin_user=admin_user, admin_pass=admin_pass)
    if grafana_url:
        for f in (DASHBOARDS_DIR / 'grafana-sg-playwright-metrics.json',):
            if f.exists():
                _do_import_grafana(grafana_url, f, c, amp_ds)
    _check_os_dashboards(ep, r, c, admin_user=admin_user, admin_pass=admin_pass)
    c.print()


# ── dashboard-check ────────────────────────────────────────────────────────────

@os_app.command('dashboard-check')
def cmd_dashboard_check(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Verify index patterns and saved objects are visible in OpenSearch Dashboards."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    c              = Console(highlight=False)
    ok             = _check_os_dashboards(ep, r, c, admin_user=admin_user, admin_pass=admin_pass)
    if not ok:
        raise typer.Exit(1)


# ── dashboard-export ───────────────────────────────────────────────────────────

@os_app.command('dashboard-export')
def cmd_dashboard_export(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    output_dir  : Optional[str] = typer.Option(None, '--output-dir', '-o'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    admin_user  : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass  : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Export OpenSearch saved objects (and Grafana dashboards) to a local directory."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    out            = Path(output_dir) if output_dir else _backup_path(stack_name) / 'dashboards'
    out.mkdir(parents=True, exist_ok=True)
    c              = Console(highlight=False)
    c.print(f'\n  Exporting dashboards for [bold]{stack_name}[/] → {out}\n')
    _do_export_os_saved_objects(ep, r, out / 'opensearch-saved-objects.ndjson', c,
                                admin_user=admin_user, admin_pass=admin_pass)
    if grafana_url:
        gdir = out / 'grafana'
        gdir.mkdir(exist_ok=True)
        _do_export_grafana(grafana_url, gdir, c)
    c.print(f'\n  [green]✓ Done[/]  →  {out}\n')


# ── data-export ────────────────────────────────────────────────────────────────

@os_app.command('data-export')
def cmd_data_export(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    output_dir : Optional[str] = typer.Option(None, '--output-dir', '-o'),
    index      : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Export all OpenSearch log documents to NDJSON via the scroll API."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    out            = Path(output_dir) if output_dir else _backup_path(stack_name)
    out.mkdir(parents=True, exist_ok=True)
    dest           = out / f'{index}.ndjson'
    auth           = (admin_user, admin_pass) if admin_user else None
    c              = Console(highlight=False)
    c.print(f'\n  Exporting [bold]{index}[/] from {stack_name!r} → {dest}\n')
    n              = _scroll_export(ep, r, index, dest, c, auth=auth)
    c.print(f'\n  [green]✓ Exported {n:,} documents[/]  →  {dest}\n')


# ── data-import ────────────────────────────────────────────────────────────────

@os_app.command('data-import')
def cmd_data_import(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    input_file : Optional[str] = typer.Option(None, '--input-file', '-i'),
    index      : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Bulk-import an NDJSON file of log documents into an OpenSearch index."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    src = (Path(input_file) if input_file
           else _latest_backup(stack_name) / f'{index}.ndjson' if _latest_backup(stack_name)
           else None)
    if not src or not src.exists():
        typer.echo('No input file. Pass --input-file or run ob backup first.', err=True)
        raise typer.Exit(1)
    auth = (admin_user, admin_pass) if admin_user else None
    c    = Console(highlight=False)
    c.print(f'\n  Importing {src} → [bold]{stack_name}[/] / {index!r}\n')
    n    = _bulk_import(ep, r, index, src, c, auth=auth)
    c.print(f'\n  [green]✓ Imported {n:,} documents[/]\n')


# ── index-list ─────────────────────────────────────────────────────────────────

@os_app.command('index-list')
def cmd_index_list(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    pattern    : str           = typer.Option('*', '--pattern', '-p'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """List all indices in the OpenSearch domain."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    auth           = (admin_user, admin_pass) if admin_user else None
    c              = Console(highlight=False)
    c.print(f'\n  Indices in [bold]{stack_name}[/]\n')
    resp = _os_req('GET', f'https://{ep}/_cat/indices/{pattern}?format=json&s=index', r, auth=auth)
    if resp.status_code >= 300:
        c.print(f'  [red]✗ HTTP {resp.status_code}:[/] {resp.text[:300]}')
        if resp.status_code == 403 and not admin_user:
            c.print('  Tip: set OB_OS_ADMIN_USER / OB_OS_ADMIN_PASS to use basic auth instead of SigV4.')
        raise typer.Exit(1)
    indices = resp.json()
    tbl = Table(show_header=True, header_style='bold', box=None)
    tbl.add_column('Index')
    tbl.add_column('Health', justify='center')
    tbl.add_column('Status', justify='center')
    tbl.add_column('Docs',   justify='right')
    tbl.add_column('Size',   justify='right')
    for idx in indices:
        health = idx.get('health', '?')
        hcolor = {'green': 'green', 'yellow': 'yellow', 'red': 'red'}.get(health, '')
        tbl.add_row(
            idx.get('index', '?'),
            f'[{hcolor}]{health}[/{hcolor}]' if hcolor else health,
            idx.get('status', '?'),
            idx.get('docs.count', '0'),
            idx.get('store.size', '?'),
        )
    c.print(tbl)
    c.print()


# ── index-info ─────────────────────────────────────────────────────────────────

@os_app.command('index-info')
def cmd_index_info(
    index_name : str           = typer.Argument(...),
    name       : Optional[str] = typer.Option(None, '--stack'),
    region     : Optional[str] = typer.Option(None, '--region'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Show mapping, settings, and doc count for an OpenSearch index."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    auth           = (admin_user, admin_pass) if admin_user else None
    c              = Console(highlight=False)
    c.print(f'\n  [bold]{index_name}[/] on [bold]{stack_name}[/]\n')
    for suffix, label in (('/_count', 'Doc count'), ('/_mapping', 'Mapping'), ('/_settings', 'Settings')):
        resp = _os_req('GET', f'https://{ep}/{index_name}{suffix}', r, auth=auth)
        c.print(f'  [bold]{label}[/]  (HTTP {resp.status_code})')
        if resp.status_code < 300:
            c.print(f'    {json.dumps(resp.json(), indent=2)[:800]}')
        else:
            c.print(f'    [red]{resp.text[:200]}[/]')
        c.print()


# ── index-delete ───────────────────────────────────────────────────────────────

@os_app.command('index-delete')
def cmd_index_delete(
    index_name : str           = typer.Argument(...),
    name       : Optional[str] = typer.Option(None, '--stack'),
    region     : Optional[str] = typer.Option(None, '--region'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
    yes        : bool          = typer.Option(False, '--yes', '-y'),
):
    """Delete an OpenSearch index and all its documents. Irreversible."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    auth           = (admin_user, admin_pass) if admin_user else None
    c              = Console(highlight=False)
    if not yes:
        if not typer.confirm(f'\n  Permanently delete index {index_name!r} on {stack_name!r}?',
                             default=False):
            raise typer.Exit(0)
    resp = _os_req('DELETE', f'https://{ep}/{index_name}', r, auth=auth)
    if resp.status_code < 300:
        c.print(f'\n  [green]✓ Index {index_name!r} deleted[/]\n')
    else:
        c.print(f'\n  [red]✗ HTTP {resp.status_code}:[/] {resp.text[:300]}\n')
        raise typer.Exit(1)


# ── pattern-list ───────────────────────────────────────────────────────────────

@os_app.command('pattern-list')
def cmd_pattern_list(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """List all index patterns in OpenSearch Dashboards (global tenant)."""
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    auth           = (admin_user, admin_pass) if admin_user else None
    hdrs           = {'Content-Type': 'application/json', 'osd-xsrf': 'true',
                      'securitytenant': 'global'}
    c              = Console(highlight=False)
    resp = requests.get(
        f'https://{ep}/_dashboards/api/saved_objects/_find?type=index-pattern&per_page=100',
        headers=hdrs, auth=auth, timeout=15)
    if resp.status_code >= 300:
        c.print(f'  [red]✗ HTTP {resp.status_code}:[/] {resp.text[:300]}')
        raise typer.Exit(1)
    patterns = resp.json().get('saved_objects', [])
    c.print(f'\n  Index patterns in [bold]{stack_name}[/] (global tenant)\n')
    if not patterns:
        c.print('  (none)\n')
        return
    tbl = Table(show_header=True, header_style='bold', box=None)
    tbl.add_column('ID')
    tbl.add_column('Title')
    tbl.add_column('Time field')
    for p in patterns:
        attrs = p.get('attributes', {})
        tbl.add_row(p.get('id', '?'), attrs.get('title', '?'), attrs.get('timeFieldName', '—'))
    c.print(tbl)
    c.print()


# ── pattern-create ─────────────────────────────────────────────────────────────

@os_app.command('pattern-create')
def cmd_pattern_create(
    pattern_id : str           = typer.Argument(...),
    name       : Optional[str] = typer.Option(None, '--stack'),
    region     : Optional[str] = typer.Option(None, '--region'),
    time_field : str           = typer.Option('@timestamp', '--time-field'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Create an index pattern in OpenSearch Dashboards (global tenant)."""
    if not admin_user or not admin_pass:
        typer.echo('\nError: admin credentials required.\n'
                   '  export OB_OS_ADMIN_USER=admin\n'
                   '  export OB_OS_ADMIN_PASS="<master-password>"\n', err=True)
        raise typer.Exit(1)
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    auth           = (admin_user, admin_pass)
    hdrs           = {'Content-Type': 'application/json', 'osd-xsrf': 'true',
                      'securitytenant': 'global'}
    base           = f'https://{ep}/_dashboards'
    body           = {'attributes': {'title': pattern_id, 'timeFieldName': time_field}}
    url            = f'{base}/api/saved_objects/index-pattern/{pattern_id}?overwrite=true'
    resp           = requests.post(url, data=json.dumps(body), headers=hdrs, auth=auth, timeout=30)
    c              = Console(highlight=False)
    if resp.status_code < 300 and _verify_index_pattern_exists(base, hdrs, auth, pattern_id):
        c.print(f'\n  [green]✓ Index pattern {pattern_id!r} created in {stack_name!r}[/]\n')
    else:
        c.print(f'\n  [red]✗ HTTP {resp.status_code}:[/] {resp.text[:400]}\n')
        raise typer.Exit(1)


# ── pattern-delete ─────────────────────────────────────────────────────────────

@os_app.command('pattern-delete')
def cmd_pattern_delete(
    pattern_id : str           = typer.Argument(...),
    name       : Optional[str] = typer.Option(None, '--stack'),
    region     : Optional[str] = typer.Option(None, '--region'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
    yes        : bool          = typer.Option(False, '--yes', '-y'),
):
    """Delete an index pattern from OpenSearch Dashboards (global tenant)."""
    if not admin_user or not admin_pass:
        typer.echo('\nError: admin credentials required.\n'
                   '  export OB_OS_ADMIN_USER=admin\n'
                   '  export OB_OS_ADMIN_PASS="<master-password>"\n', err=True)
        raise typer.Exit(1)
    r              = region or _region()
    ep, stack_name = _os_resolve(name, r)
    c              = Console(highlight=False)
    if not yes:
        if not typer.confirm(f'\n  Delete index pattern {pattern_id!r} from {stack_name!r}?',
                             default=False):
            raise typer.Exit(0)
    auth = (admin_user, admin_pass)
    hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true', 'securitytenant': 'global'}
    base = f'https://{ep}/_dashboards'
    resp = requests.delete(f'{base}/api/saved_objects/index-pattern/{pattern_id}',
                           headers=hdrs, auth=auth, timeout=15)
    if resp.status_code < 300:
        c.print(f'\n  [green]✓ Index pattern {pattern_id!r} deleted from {stack_name!r}[/]\n')
    else:
        c.print(f'\n  [red]✗ HTTP {resp.status_code}:[/] {resp.text[:300]}\n')
        raise typer.Exit(1)
