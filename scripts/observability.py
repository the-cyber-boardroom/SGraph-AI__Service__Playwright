# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — observability.py
# CLI entry-point: ob
# Manages AMP workspace + OpenSearch domain pairs (observability stacks).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import string
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import boto3
import requests
import typer
from botocore.auth      import SigV4Auth
from botocore.awsrequest import AWSRequest
from rich.console import Console
from rich.table   import Table

from osbot_aws.AWS_Config import AWS_Config

app = typer.Typer(name='ob', help='Observability stack management (AMP + OpenSearch).',
                  no_args_is_help=True)

# ── Constants ──────────────────────────────────────────────────────────────────

OPENSEARCH_ENGINE    = 'OpenSearch_2.17'
OPENSEARCH_INSTANCE  = 't3.small.search'   # smallest instance with FGAC support
OPENSEARCH_VOLUME_GB = 10                  # minimum gp3 volume
OPENSEARCH_INDEX     = 'sg-playwright-logs'
IAM_ROLE_NAME        = 'playwright-ec2'

DASHBOARDS_DIR = Path(__file__).parent.parent / 'library' / 'docs' / 'ops' / 'dashboards'
BACKUPS_DIR    = Path.home() / '.sg-playwright' / 'observability-backups'

SCROLL_TTL  = '2m'
SCROLL_SIZE = 1000
BULK_CHUNK  = 500

# ── AWS region / account helpers ───────────────────────────────────────────────

def _region() -> str:
    try:
        return AWS_Config().aws_session_region_name()
    except Exception:
        return 'eu-west-2'


def _account() -> str:
    try:
        return boto3.client('sts').get_caller_identity()['Account']
    except Exception:
        return 'unknown'


# ── SigV4 HTTP helper ──────────────────────────────────────────────────────────

def _sigv4(method: str, url: str, region: str,
           body: bytes = b'', extra_headers: dict = None) -> requests.Response:
    """Sign and execute an HTTP request against OpenSearch (service='es')."""
    session = boto3.Session()
    creds   = session.get_credentials()
    headers = {'Content-Type': 'application/json', **(extra_headers or {})}
    req     = AWSRequest(method=method.upper(), url=url, data=body, headers=headers)
    SigV4Auth(creds, 'es', region).add_auth(req)
    return requests.request(method, url, data=body, headers=dict(req.headers), timeout=60)


# ── Stack discovery ────────────────────────────────────────────────────────────

def _amp_workspaces(region: str) -> dict:
    """alias → workspace dict for every AMP workspace in the region."""
    out = {}
    try:
        amp   = boto3.client('amp', region_name=region)
        pages = amp.get_paginator('list_workspaces').paginate()
        for page in pages:
            for ws in page.get('workspaces', []):
                alias      = ws.get('alias', ws['workspaceId'])
                out[alias] = ws
    except Exception:
        pass
    return out


def _os_domains(region: str) -> dict:
    """domain_name → domain status dict for every OpenSearch domain."""
    out = {}
    try:
        osc   = boto3.client('opensearch', region_name=region)
        names = [d['DomainName'] for d in osc.list_domain_names().get('DomainNames', [])]
        if names:
            for ds in osc.describe_domains(DomainNames=names).get('DomainStatusList', []):
                out[ds['DomainName']] = ds
    except Exception:
        pass
    return out


def _list_stacks(region: str) -> list:
    """Return all stacks — AMP alias / OpenSearch domain name pairs."""
    amp_ws  = _amp_workspaces(region)
    os_doms = _os_domains(region)
    out     = []
    for name in sorted(set(amp_ws) | set(os_doms)):
        out.append({'name': name, 'amp': amp_ws.get(name), 'opensearch': os_doms.get(name)})
    return out


def _resolve_stack(name: Optional[str], region: str) -> str:
    """Return a stack name: given > single-existing > interactive prompt."""
    if name:
        return name
    stacks = _list_stacks(region)
    if not stacks:
        typer.echo('No observability stacks found. Run: ob create <name>', err=True)
        raise typer.Exit(1)
    if len(stacks) == 1:
        return stacks[0]['name']
    c = Console(highlight=False)
    c.print('\n  Select an observability stack:\n')
    for i, s in enumerate(stacks, 1):
        c.print(f'  {i}.  {s["name"]}')
    choice = typer.prompt('\n  Stack number')
    try:
        return stacks[int(choice) - 1]['name']
    except (ValueError, IndexError):
        typer.echo('Invalid selection.', err=True)
        raise typer.Exit(1)


# ── Small domain helpers ───────────────────────────────────────────────────────

def _os_endpoint(domain_status: dict) -> str:
    return (domain_status.get('Endpoint')
            or domain_status.get('Endpoints', {}).get('vpc', ''))


def _amp_rw_url(workspace: dict, region: str) -> str:
    ws_id = workspace['workspaceId']
    return (f'https://aps-workspaces.{region}.amazonaws.com'
            f'/workspaces/{ws_id}/api/v1/remote_write')


def _os_doc_count(endpoint: str, region: str) -> int:
    try:
        r = _sigv4('GET', f'https://{endpoint}/{OPENSEARCH_INDEX}/_count', region)
        if r.status_code == 200:
            return r.json().get('count', 0)
    except Exception:
        pass
    return -1


def _generate_os_password() -> str:
    """Generate a 16-char password satisfying OpenSearch complexity rules."""
    specials = '!@#$%^&*'
    alphabet = string.ascii_letters + string.digits + specials
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(16))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in specials for c in pwd)):
            return pwd


def _backup_path(stack_name: str) -> Path:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')
    return BACKUPS_DIR / stack_name / ts


def _latest_backup(stack_name: str) -> Optional[Path]:
    d = BACKUPS_DIR / stack_name
    if not d.exists():
        return None
    dirs = sorted(d.iterdir(), reverse=True)
    return dirs[0] if dirs else None


# ── list ───────────────────────────────────────────────────────────────────────

@app.command('list')
def cmd_list(region: Optional[str] = typer.Option(None, '--region')):
    """List all observability stacks."""
    r      = region or _region()
    stacks = _list_stacks(r)
    c      = Console(highlight=False)
    if not stacks:
        c.print('\n  [dim]No stacks found.[/]  Run: [bold]ob create <name>[/]\n')
        return
    t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
    t.add_column('Name',        style='bold')
    t.add_column('AMP')
    t.add_column('OpenSearch')
    t.add_column('Endpoint', style='dim')
    for s in stacks:
        amp_st = s['amp']['status']       if s['amp']         else '[red]missing[/]'
        os_st  = ('[yellow]processing[/]' if s['opensearch'] and s['opensearch'].get('Processing')
                  else 'active'           if s['opensearch']
                  else '[red]missing[/]')
        ep     = (_os_endpoint(s['opensearch'])[:55] if s['opensearch'] else '')
        t.add_row(s['name'], amp_st, os_st, ep)
    c.print()
    c.print(t)
    c.print()


# ── info ───────────────────────────────────────────────────────────────────────

@app.command('info')
def cmd_info(name:   Optional[str] = typer.Argument(None),
             region: Optional[str] = typer.Option(None, '--region')):
    """Show full details and ready-to-use env-var exports for a stack."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name, {'name': stack_name, 'amp': None, 'opensearch': None})
    c          = Console(highlight=False)
    c.print(f'\n  [bold]Stack:[/] {stack_name}\n')

    if s['amp']:
        ws     = s['amp']
        rw_url = _amp_rw_url(ws, r)
        c.print('  [bold cyan]AMP[/]')
        c.print(f'    Workspace ID : {ws["workspaceId"]}')
        c.print(f'    Status       : {ws["status"]}')
        c.print(f'    Remote Write : {rw_url}')
        c.print()
    else:
        c.print('  [bold cyan]AMP[/]  [red]not found[/]\n')

    if s['opensearch']:
        ds      = s['opensearch']
        ep      = _os_endpoint(ds)
        doc_ct  = _os_doc_count(ep, r) if ep else -1
        status  = 'processing' if ds.get('Processing') else 'active'
        c.print('  [bold cyan]OpenSearch[/]')
        c.print(f'    Domain    : {ds["DomainName"]}')
        c.print(f'    Engine    : {ds.get("EngineVersion", "?")}')
        c.print(f'    Status    : {status}')
        c.print(f'    Endpoint  : {ep}')
        c.print(f'    Dashboards: https://{ep}/_dashboards')
        c.print(f'    Documents : {doc_ct:,}  (index: {OPENSEARCH_INDEX!r})')
        c.print()
    else:
        c.print('  [bold cyan]OpenSearch[/]  [red]not found[/]\n')

    if s['amp'] and s['opensearch']:
        ep = _os_endpoint(s['opensearch'])
        if ep:
            c.print('  [bold]Env exports for sp create:[/]')
            c.print(f'    export AMP_REMOTE_WRITE_URL="{_amp_rw_url(s["amp"], r)}"')
            c.print(f'    export OPENSEARCH_ENDPOINT="{ep}"')
            c.print()


# ── wait (standalone poll for an in-progress creation) ────────────────────────

def _wait_active(amp_client, os_client, ws_id: str, domain: str, c: Console):
    """Poll until AMP workspace and OpenSearch domain are both active."""
    c.print('  Polling for ACTIVE status (AMP: ~30s, OpenSearch: ~15-20 min)…')

    # AMP — fast, poll every 15s up to 5 min
    for attempt in range(20):
        ws = amp_client.describe_workspace(workspaceId=ws_id)['workspace']
        if ws['status'] == 'ACTIVE':
            c.print(f'  [green]✓ AMP ACTIVE[/]  ({attempt * 15}s)')
            break
        time.sleep(15)
    else:
        c.print('  [yellow]⚠ AMP did not reach ACTIVE in 5 min — continuing anyway[/]')

    # OpenSearch — slow, poll every 30s up to 30 min
    for attempt in range(60):
        ds = os_client.describe_domain(DomainName=domain)['DomainStatus']
        if not ds.get('Processing', True) and ds.get('Endpoint'):
            c.print(f'  [green]✓ OpenSearch ACTIVE[/]  ({attempt * 30}s)')
            return
        elapsed = attempt * 30
        c.print(f'  [dim]  OpenSearch: processing… ({elapsed}s elapsed)[/]')
        time.sleep(30)
    c.print('  [yellow]⚠ OpenSearch did not reach ACTIVE in 30 min — check AWS console[/]')


@app.command('wait')
def cmd_wait(name:   Optional[str] = typer.Argument(None),
             region: Optional[str] = typer.Option(None, '--region')):
    """Poll until a stack's AMP workspace and OpenSearch domain are both active."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    c          = Console(highlight=False)
    if not s or not s['amp'] or not s['opensearch']:
        c.print(f'[red]Stack {stack_name!r} incomplete — run ob info to diagnose.[/]')
        raise typer.Exit(1)
    ws_id  = s['amp']['workspaceId']
    amp    = boto3.client('amp',        region_name=r)
    osc    = boto3.client('opensearch', region_name=r)
    c.print(f'\n  Waiting for [bold]{stack_name}[/]\n')
    _wait_active(amp, osc, ws_id, stack_name, c)
    c.print()


# ── create ─────────────────────────────────────────────────────────────────────

@app.command('create')
def cmd_create(
    name     : str           = typer.Argument(..., help='Stack name — becomes AMP alias and OpenSearch domain name.'),
    region   : Optional[str] = typer.Option(None, '--region'),
    no_wait  : bool          = typer.Option(False, '--no-wait', help='Return immediately; use ob wait later.'),
    no_import: bool          = typer.Option(False, '--no-import', help='Skip auto-importing dashboards.'),
):
    """Create an AMP workspace + OpenSearch domain, then wait until both are active."""
    r       = region or _region()
    account = _account()
    c       = Console(highlight=False)
    amp     = boto3.client('amp',        region_name=r)
    osc     = boto3.client('opensearch', region_name=r)

    c.print(f'\n  [bold]Creating:[/] {name!r}  [dim]({r} / {account})[/]\n')

    # ── AMP ────────────────────────────────────────────────────────────────
    existing_ws = amp.list_workspaces(alias=name).get('workspaces', [])
    if existing_ws:
        ws_id = existing_ws[0]['workspaceId']
        c.print(f'  [yellow]AMP workspace exists[/]  {ws_id}')
    else:
        ws_id = amp.create_workspace(alias=name)['workspaceId']
        c.print(f'  [green]✓ AMP workspace created[/]  {ws_id}')

    # ── OpenSearch ─────────────────────────────────────────────────────────
    master_password = None
    try:
        osc.describe_domain(DomainName=name)
        c.print(f'  [yellow]OpenSearch domain exists[/]  {name}')
    except osc.exceptions.ResourceNotFoundException:
        master_password = _generate_os_password()
        osc.create_domain(
            DomainName   = name,
            EngineVersion= OPENSEARCH_ENGINE,
            ClusterConfig= {'InstanceType': OPENSEARCH_INSTANCE, 'InstanceCount': 1},
            EBSOptions   = {'EBSEnabled': True, 'VolumeType': 'gp3',
                            'VolumeSize': OPENSEARCH_VOLUME_GB},
            AccessPolicies = json.dumps({
                'Version': '2012-10-17',
                'Statement': [{'Effect': 'Allow', 'Principal': {'AWS': '*'},
                               'Action': 'es:*',
                               'Resource': f'arn:aws:es:{r}:{account}:domain/{name}/*'}]}),
            AdvancedSecurityOptions = {
                'Enabled': True, 'InternalUserDatabaseEnabled': True,
                'MasterUserOptions': {'MasterUserName': 'admin',
                                      'MasterUserPassword': master_password}},
            NodeToNodeEncryptionOptions = {'Enabled': True},
            EncryptionAtRestOptions     = {'Enabled': True},
            DomainEndpointOptions       = {'EnforceHTTPS': True},
        )
        c.print(f'  [green]✓ OpenSearch creation started[/]  '
                f'({OPENSEARCH_INSTANCE}, {OPENSEARCH_VOLUME_GB} GB gp3, {OPENSEARCH_ENGINE})')
        c.print(f'\n  [bold yellow]Save this master password (printed once):[/]')
        c.print(f'    Username : admin')
        c.print(f'    Password : {master_password}\n')

    if no_wait:
        c.print('  [dim]--no-wait: use ob wait or ob info to track status.[/]\n')
        return

    # ── Wait ───────────────────────────────────────────────────────────────
    _wait_active(amp, osc, ws_id, name, c)

    # ── Auto-map backend role ──────────────────────────────────────────────
    ep = _os_endpoint(osc.describe_domain(DomainName=name)['DomainStatus'])
    if master_password and ep:
        role_arn = f'arn:aws:iam::{account}:role/{IAM_ROLE_NAME}'
        url      = f'https://{ep}/_plugins/_security/api/rolesmapping/all_access'
        resp     = requests.put(url,
                                data=json.dumps({'backend_roles': [role_arn]}).encode(),
                                headers={'Content-Type': 'application/json'},
                                auth=('admin', master_password), timeout=30)
        if resp.status_code < 300:
            c.print(f'  [green]✓ Backend role mapped[/]  ({role_arn})')
        else:
            c.print(f'  [yellow]⚠ Role mapping failed ({resp.status_code})[/]')
            c.print(f'    Map manually: Security → all_access → Backend roles → {role_arn}')

    # ── Auto-import dashboards ─────────────────────────────────────────────
    if not no_import and ep:
        _do_import_os_saved_objects(ep, r, c,
                                    admin_user='admin' if master_password else '',
                                    admin_pass=master_password or '')

    # ── Summary ────────────────────────────────────────────────────────────
    c.print(f'\n  [bold]Env exports for sp create:[/]')
    c.print(f'    export AMP_REMOTE_WRITE_URL="{_amp_rw_url({"workspaceId": ws_id}, r)}"')
    c.print(f'    export OPENSEARCH_ENDPOINT="{ep}"')
    c.print()


# ── delete ─────────────────────────────────────────────────────────────────────

@app.command('delete')
def cmd_delete(
    name   : Optional[str] = typer.Argument(None),
    region : Optional[str] = typer.Option(None, '--region'),
    yes    : bool          = typer.Option(False, '--yes', '-y'),
):
    """Delete an AMP workspace + OpenSearch domain. All data is permanently lost."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    c          = Console(highlight=False)
    if not yes:
        c.print(f'\n  [bold red]Permanently deletes:[/]')
        c.print(f'  • AMP workspace  alias={stack_name!r}')
        c.print(f'  • OpenSearch domain  name={stack_name!r}  (all log data)')
        if not typer.confirm('\n  Confirm?', default=False):
            raise typer.Exit(0)
    c.print()
    amp = boto3.client('amp',        region_name=r)
    osc = boto3.client('opensearch', region_name=r)
    for ws in amp.list_workspaces(alias=stack_name).get('workspaces', []):
        amp.delete_workspace(workspaceId=ws['workspaceId'])
        c.print(f'  [green]✓ AMP workspace deleted[/]  {ws["workspaceId"]}')
    try:
        osc.delete_domain(DomainName=stack_name)
        c.print(f'  [green]✓ OpenSearch deletion started[/]  (~10 min to complete)')
    except osc.exceptions.ResourceNotFoundException:
        c.print(f'  [dim]OpenSearch domain {stack_name!r} not found[/]')
    c.print()


# ── Dashboard helpers ──────────────────────────────────────────────────────────

def _do_import_os_saved_objects(endpoint: str, region: str, c: Console,
                                 ndjson_path: Optional[Path] = None,
                                 admin_user: str = '', admin_pass: str = ''):
    """POST an NDJSON file to /_dashboards/api/saved_objects/_import.

    Uses basic auth when admin_user+admin_pass are supplied (preferred — bypasses FGAC
    backend-role requirement). Falls back to SigV4 when credentials are absent.
    """
    src      = ndjson_path or (DASHBOARDS_DIR / 'opensearch-instance-lifecycle.ndjson')
    if not src.exists():
        c.print(f'  [red]✗ File not found: {src}[/]')
        return
    url      = f'https://{endpoint}/_dashboards/api/saved_objects/_import?overwrite=true'
    boundary = 'SG_OB_BOUNDARY'
    body     = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{src.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
    ).encode() + src.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    hdrs     = {'Content-Type': f'multipart/form-data; boundary={boundary}', 'osd-xsrf': 'true'}
    if admin_user and admin_pass:
        resp = requests.post(url, data=body, headers=hdrs,
                             auth=(admin_user, admin_pass), timeout=30)
    else:
        session = boto3.Session()
        creds   = session.get_credentials()
        aws_req = AWSRequest(method='POST', url=url, data=body, headers=hdrs)
        SigV4Auth(creds, 'es', region).add_auth(aws_req)
        resp    = requests.post(url, data=body, headers=dict(aws_req.headers), timeout=30)
    if resp.status_code < 300:
        c.print(f'  [green]✓ OS saved objects imported[/]  ({src.name})')
    else:
        c.print(f'  [red]✗ OS import HTTP {resp.status_code}:[/] {resp.text[:200]}')


def _do_export_os_saved_objects(endpoint: str, region: str, output: Path, c: Console):
    """Export all OpenSearch Dashboards saved objects to an NDJSON file."""
    url  = f'https://{endpoint}/_dashboards/api/saved_objects/_export'
    body = json.dumps({'type': ['index-pattern', 'visualization', 'dashboard'],
                       'includeReferencesDeep': True}).encode()
    resp = _sigv4('POST', url, region, body, {'osd-xsrf': 'true'})
    if resp.status_code < 300:
        output.write_bytes(resp.content)
        c.print(f'  [green]✓ OS saved objects exported[/]  ({len(resp.content):,} bytes → {output.name})')
    else:
        c.print(f'  [red]✗ OS export HTTP {resp.status_code}:[/] {resp.text[:200]}')


def _do_import_grafana(workspace_url: str, dash_path: Path, c: Console,
                       amp_ds: str = 'grafana-amazonprometheus-datasource'):
    """Create a short-lived AMG key, import one dashboard JSON, delete the key."""
    url      = workspace_url.rstrip('/')
    host     = url.removeprefix('https://').removeprefix('http://')
    ws_id    = host.split('.')[0]
    grafana  = boto3.client('grafana', region_name=_region())
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
            pass


def _do_export_grafana(workspace_url: str, output_dir: Path, c: Console):
    """Export all Grafana dashboards to JSON files using a short-lived VIEWER key."""
    url      = workspace_url.rstrip('/')
    host     = url.removeprefix('https://').removeprefix('http://')
    ws_id    = host.split('.')[0]
    grafana  = boto3.client('grafana', region_name=_region())
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
            pass


# ── dashboard-import ───────────────────────────────────────────────────────────

@app.command('dashboard-import')
def cmd_dashboard_import(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    amp_ds      : str           = typer.Option('grafana-amazonprometheus-datasource', '--amp-datasource'),
    admin_user  : str           = typer.Option('', '--admin-user', help='OpenSearch master username (bypasses FGAC backend-role requirement).'),
    admin_pass  : str           = typer.Option('', '--admin-pass', help='OpenSearch master password.'),
):
    """Import OpenSearch saved objects + Grafana dashboard from library/docs/ops/dashboards/."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found or missing OpenSearch domain.', err=True)
        raise typer.Exit(1)
    ep = _os_endpoint(s['opensearch'])
    c  = Console(highlight=False)
    c.print(f'\n  Importing dashboards → [bold]{stack_name}[/]\n')
    _do_import_os_saved_objects(ep, r, c, admin_user=admin_user, admin_pass=admin_pass)
    if grafana_url:
        for f in (DASHBOARDS_DIR / 'grafana-sg-playwright-metrics.json',):
            if f.exists():
                _do_import_grafana(grafana_url, f, c, amp_ds)
    c.print()


# ── dashboard-export ───────────────────────────────────────────────────────────

@app.command('dashboard-export')
def cmd_dashboard_export(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    output_dir  : Optional[str] = typer.Option(None, '--output-dir', '-o'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
):
    """Export OpenSearch saved objects (and Grafana dashboards) to a local directory."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found.', err=True)
        raise typer.Exit(1)
    ep       = _os_endpoint(s['opensearch'])
    out      = Path(output_dir) if output_dir else _backup_path(stack_name) / 'dashboards'
    out.mkdir(parents=True, exist_ok=True)
    c        = Console(highlight=False)
    c.print(f'\n  Exporting dashboards for [bold]{stack_name}[/] → {out}\n')
    _do_export_os_saved_objects(ep, r, out / 'opensearch-saved-objects.ndjson', c)
    if grafana_url:
        gdir = out / 'grafana'
        gdir.mkdir(exist_ok=True)
        _do_export_grafana(grafana_url, gdir, c)
    c.print(f'\n  [green]✓ Done[/]  →  {out}\n')


# ── Scroll / bulk helpers ──────────────────────────────────────────────────────

def _scroll_export(endpoint: str, region: str, index: str,
                   output: Path, c: Console) -> int:
    """Export all documents from an index via scroll API to an NDJSON file."""
    url  = f'https://{endpoint}/{index}/_search?scroll={SCROLL_TTL}'
    body = json.dumps({'size': SCROLL_SIZE, 'query': {'match_all': {}},
                       'sort': ['_doc']}).encode()
    resp = _sigv4('POST', url, region, body)
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
            scroll_resp = _sigv4('POST', f'https://{endpoint}/_search/scroll', region,
                                  json.dumps({'scroll': SCROLL_TTL,
                                              'scroll_id': scroll_id}).encode())
            if scroll_resp.status_code != 200:
                break
            data      = scroll_resp.json()
            scroll_id = data.get('_scroll_id', scroll_id)
    _sigv4('DELETE', f'https://{endpoint}/_search/scroll', region,
           json.dumps({'scroll_id': scroll_id}).encode())
    return count


def _bulk_import(endpoint: str, region: str, index: str,
                 src: Path, c: Console) -> int:
    """Bulk-import documents from an NDJSON file."""
    lines = [l for l in src.read_text().splitlines() if l.strip()]
    c.print(f'  Documents to import: {len(lines):,}')
    count = 0
    for i in range(0, len(lines), BULK_CHUNK):
        chunk = lines[i:i + BULK_CHUNK]
        body  = ''
        for line in chunk:
            body  += json.dumps({'index': {'_index': index}}) + '\n' + line + '\n'
            count += 1
        resp = _sigv4('POST', f'https://{endpoint}/_bulk', region, body.encode(),
                      {'Content-Type': 'application/x-ndjson'})
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


# ── data-export ────────────────────────────────────────────────────────────────

@app.command('data-export')
def cmd_data_export(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    output_dir : Optional[str] = typer.Option(None, '--output-dir', '-o'),
    index      : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
):
    """Export all OpenSearch log documents to NDJSON via the scroll API."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found.', err=True)
        raise typer.Exit(1)
    ep   = _os_endpoint(s['opensearch'])
    out  = Path(output_dir) if output_dir else _backup_path(stack_name)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f'{index}.ndjson'
    c    = Console(highlight=False)
    c.print(f'\n  Exporting [bold]{index}[/] from {stack_name!r} → {dest}\n')
    n    = _scroll_export(ep, r, index, dest, c)
    c.print(f'\n  [green]✓ Exported {n:,} documents[/]  →  {dest}\n')


# ── data-import ────────────────────────────────────────────────────────────────

@app.command('data-import')
def cmd_data_import(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    input_file : Optional[str] = typer.Option(None, '--input-file', '-i'),
    index      : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
):
    """Bulk-import an NDJSON file of log documents into an OpenSearch index."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found.', err=True)
        raise typer.Exit(1)
    ep  = _os_endpoint(s['opensearch'])
    src = Path(input_file) if input_file else _latest_backup(stack_name) / f'{index}.ndjson' if _latest_backup(stack_name) else None
    if not src or not src.exists():
        typer.echo(f'No input file. Pass --input-file or run ob backup first.', err=True)
        raise typer.Exit(1)
    c = Console(highlight=False)
    c.print(f'\n  Importing {src} → [bold]{stack_name}[/] / {index!r}\n')
    n = _bulk_import(ep, r, index, src, c)
    c.print(f'\n  [green]✓ Imported {n:,} documents[/]\n')


# ── backup ─────────────────────────────────────────────────────────────────────

@app.command('backup')
def cmd_backup(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    output_dir  : Optional[str] = typer.Option(None, '--output-dir', '-o'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    index       : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
):
    """Full backup: data-export + dashboard-export into a timestamped directory."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found.', err=True)
        raise typer.Exit(1)
    ep  = _os_endpoint(s['opensearch'])
    ts  = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')
    out = Path(output_dir) if output_dir else BACKUPS_DIR / stack_name / ts
    out.mkdir(parents=True, exist_ok=True)
    c   = Console(highlight=False)
    c.print(f'\n  [bold]Backup:[/] {stack_name!r}  →  {out}\n')

    ndjson = out / f'{index}.ndjson'
    count  = _scroll_export(ep, r, index, ndjson, c)

    ddir = out / 'dashboards'
    ddir.mkdir(exist_ok=True)
    _do_export_os_saved_objects(ep, r, ddir / 'opensearch-saved-objects.ndjson', c)
    if grafana_url:
        gdir = ddir / 'grafana'
        gdir.mkdir(exist_ok=True)
        _do_export_grafana(grafana_url, gdir, c)

    manifest = {'stack': stack_name, 'timestamp': ts, 'region': r,
                'index': index, 'doc_count': count,
                'amp_workspace_id': s['amp']['workspaceId'] if s['amp'] else None,
                'opensearch_endpoint': ep}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    c.print(f'\n  [green]✓ Backup complete[/]  {count:,} docs  →  {out}\n')


# ── restore ────────────────────────────────────────────────────────────────────

@app.command('restore')
def cmd_restore(
    name        : Optional[str] = typer.Argument(None, help='Target stack to restore into.'),
    region      : Optional[str] = typer.Option(None, '--region'),
    backup_dir  : Optional[str] = typer.Option(None, '--backup-dir', '-b',
                                               help='Exact backup directory (contains manifest.json).'),
    from_stack  : Optional[str] = typer.Option(None, '--from',
                                               help='Source stack — uses its latest backup.'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    index       : str           = typer.Option(OPENSEARCH_INDEX, '--index'),
):
    """Restore data + dashboards from a backup directory into a stack."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Target stack {stack_name!r} not found.', err=True)
        raise typer.Exit(1)
    ep   = _os_endpoint(s['opensearch'])
    bdir = (Path(backup_dir) if backup_dir
            else _latest_backup(from_stack) if from_stack
            else _latest_backup(stack_name))
    if not bdir or not bdir.exists():
        typer.echo('No backup found. Use --backup-dir or --from <stack>.', err=True)
        raise typer.Exit(1)
    c        = Console(highlight=False)
    manifest = json.loads((bdir / 'manifest.json').read_text()) if (bdir / 'manifest.json').exists() else {}
    c.print(f'\n  [bold]Restore:[/] {bdir}  →  {stack_name!r}\n')
    if manifest:
        c.print(f'  Source: {manifest.get("stack")} / {manifest.get("timestamp")} / '
                f'{manifest.get("doc_count", "?")} docs\n')

    ndjson = bdir / f'{index}.ndjson'
    if ndjson.exists():
        n = _bulk_import(ep, r, index, ndjson, c)
        c.print(f'  [green]✓ Imported {n:,} documents[/]')
    else:
        c.print(f'  [dim]No data file at {ndjson}[/]')

    saved_obj = bdir / 'dashboards' / 'opensearch-saved-objects.ndjson'
    if saved_obj.exists():
        _do_import_os_saved_objects(ep, r, c, saved_obj)

    if grafana_url:
        gdir = bdir / 'dashboards' / 'grafana'
        if gdir.exists():
            for f in gdir.glob('*.json'):
                _do_import_grafana(grafana_url, f, c)

    c.print(f'\n  [green]✓ Restore complete[/]\n')


if __name__ == '__main__':
    app()
