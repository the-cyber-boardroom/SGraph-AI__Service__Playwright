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

app = typer.Typer(help='Observability stack management (AMP + OpenSearch).',
                  no_args_is_help=True)

# ── Constants ──────────────────────────────────────────────────────────────────

OPENSEARCH_ENGINE    = 'OpenSearch_3.5'
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


def _amg_workspaces(region: str) -> dict:
    """workspace_name → workspace dict for every AMG workspace in the region."""
    out = {}
    try:
        grafana = boto3.client('grafana', region_name=region)
        pages   = grafana.get_paginator('list_workspaces').paginate()
        for page in pages:
            for ws in page.get('workspaces', []):
                out[ws['name']] = ws
    except Exception:
        pass
    return out


def _list_stacks(region: str) -> list:
    """Return all stacks — AMP alias / OpenSearch domain / AMG workspace triples."""
    amp_ws  = _amp_workspaces(region)
    os_doms = _os_domains(region)
    amg_ws  = _amg_workspaces(region)
    out     = []
    for name in sorted(set(amp_ws) | set(os_doms) | set(amg_ws)):
        out.append({'name': name, 'amp': amp_ws.get(name),
                    'opensearch': os_doms.get(name), 'grafana': amg_ws.get(name)})
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
    t.add_column('Grafana')
    t.add_column('Endpoint', style='dim')
    for s in stacks:
        amp_st = (s['amp'].get('status', {}).get('statusCode', '?')
                  if s['amp'] else '[red]missing[/]')
        os_st  = ('[yellow]processing[/]' if s['opensearch'] and s['opensearch'].get('Processing')
                  else 'active'           if s['opensearch']
                  else '[red]missing[/]')
        g_st   = (s['grafana'].get('status', '?') if s.get('grafana')
                  else '[red]missing[/]')
        ep     = (_os_endpoint(s['opensearch'])[:55] if s['opensearch'] else '')
        t.add_row(s['name'], amp_st, os_st, g_st, ep)
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
    s          = by_name.get(stack_name, {'name': stack_name, 'amp': None, 'opensearch': None, 'grafana': None})
    c          = Console(highlight=False)
    c.print(f'\n  [bold]Stack:[/] {stack_name}\n')

    if s['amp']:
        ws     = s['amp']
        rw_url = _amp_rw_url(ws, r)
        c.print('  [bold cyan]AMP[/]')
        c.print(f'    Workspace ID : {ws["workspaceId"]}')
        c.print(f'    Status       : {ws.get("status", {}).get("statusCode", "?")}')
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

    if s.get('grafana'):
        gws = s['grafana']
        ep  = gws.get('endpoint', '')
        gid = gws.get('id', '')
        c.print('  [bold cyan]Grafana (AMG)[/]')
        c.print(f'    Workspace ID : {gid}')
        c.print(f'    Status       : {gws.get("status", "?")}')
        if ep:
            c.print(f'    URL          : https://{ep}')
        c.print()
    else:
        c.print('  [bold cyan]Grafana (AMG)[/]  [dim]not found — run ob create to provision[/]\n')

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
        if ws.get('status', {}).get('statusCode') == 'ACTIVE':
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


# ── AMG helpers ────────────────────────────────────────────────────────────────

def _map_backend_role(endpoint: str, role_arn: str, admin_user: str, admin_pass: str, c: Console):
    """GET existing all_access mapping, merge role_arn in, PUT back — preserving all fields."""
    url  = f'https://{endpoint}/_plugins/_security/api/rolesmapping/all_access'
    auth = (admin_user, admin_pass)
    try:
        current = {}
        get_resp = requests.get(url, auth=auth, timeout=30)
        if get_resp.status_code == 200:
            current = get_resp.json().get('all_access', {})
        backend_roles = list(current.get('backend_roles', []))
        users         = list(current.get('users', []))
        hosts         = list(current.get('hosts', []))
        if role_arn in backend_roles:
            c.print(f'  [dim]Backend role already mapped:[/]  {role_arn.split("/")[-1]}')
            return True
        backend_roles.append(role_arn)
        put_resp = requests.put(url,
                                json={'backend_roles': backend_roles, 'users': users, 'hosts': hosts},
                                headers={'Content-Type': 'application/json'},
                                auth=auth, timeout=30)
        if put_resp.status_code < 300:
            c.print(f'  [green]✓ Backend role mapped[/]  {role_arn.split("/")[-1]}')
            return True
        c.print(f'  [yellow]⚠ Role mapping failed ({put_resp.status_code})[/]')
        c.print(f'    Map manually: Security → all_access → Backend roles → {role_arn}')
        return False
    except Exception as e:
        c.print(f'  [yellow]⚠ Role mapping error:[/] {e}')
        return False


def _map_admin_user(endpoint: str, admin_user: str, admin_pass: str, c: Console):
    """Add admin_user to all_access users list so Dashboards grants tenant access."""
    url  = f'https://{endpoint}/_plugins/_security/api/rolesmapping/all_access'
    auth = (admin_user, admin_pass)
    try:
        current = {}
        get_resp = requests.get(url, auth=auth, timeout=30)
        if get_resp.status_code == 200:
            current = get_resp.json().get('all_access', {})
        backend_roles = list(current.get('backend_roles', []))
        users         = list(current.get('users', []))
        hosts         = list(current.get('hosts', []))
        if admin_user in users:
            c.print(f'  [dim]Admin user already in all_access mapping[/]')
            return True
        users.append(admin_user)
        put_resp = requests.put(url,
                                json={'backend_roles': backend_roles, 'users': users, 'hosts': hosts},
                                headers={'Content-Type': 'application/json'},
                                auth=auth, timeout=30)
        if put_resp.status_code < 300:
            c.print(f'  [green]✓ Admin user mapped to all_access[/]  (enables Dashboards tenant access)')
            return True
        c.print(f'  [yellow]⚠ Admin user mapping failed ({put_resp.status_code})[/]')
        return False
    except Exception as e:
        c.print(f'  [yellow]⚠ Admin mapping error:[/] {e}')
        return False


GRAFANA_ROLE_NAME = 'sg-playwright-grafana'


def _ensure_grafana_role(account: str, r: str) -> str:
    """Return ARN of sg-playwright-grafana IAM role, creating it if absent."""
    iam = boto3.client('iam')
    try:
        return iam.get_role(RoleName=GRAFANA_ROLE_NAME)['Role']['Arn']
    except iam.exceptions.NoSuchEntityException:
        pass
    trust = json.dumps({
        'Version': '2012-10-17',
        'Statement': [{'Effect': 'Allow',
                       'Principal': {'Service': 'grafana.amazonaws.com'},
                       'Action': 'sts:AssumeRole',
                       'Condition': {
                           'StringEquals':  {'aws:SourceAccount': account},
                           'StringLike':    {'aws:SourceArn': f'arn:aws:grafana:{r}:{account}:/workspaces/*'}
                       }}]
    })
    arn = iam.create_role(RoleName=GRAFANA_ROLE_NAME,
                          AssumeRolePolicyDocument=trust,
                          Description='AMG workspace role for SG Playwright observability')['Role']['Arn']
    for policy in ('arn:aws:iam::aws:policy/AmazonPrometheusQueryAccess',
                   'arn:aws:iam::aws:policy/AWSGrafanaWorkspacePermissionManagement'):
        try:
            iam.attach_role_policy(RoleName=GRAFANA_ROLE_NAME, PolicyArn=policy)
        except Exception:
            pass
    return arn


def _start_amg_workspace(name: str, r: str, account: str, c: Console) -> Optional[str]:
    """Kick off AMG workspace creation. Returns ws_id immediately (no waiting)."""
    grafana  = boto3.client('grafana', region_name=r)
    existing = _amg_workspaces(r)
    if name in existing:
        ws_id = existing[name]['id']
        c.print(f'  [yellow]AMG workspace exists[/]  {ws_id}')
        return ws_id
    try:
        role_arn = _ensure_grafana_role(account, r)
        ws_id = grafana.create_workspace(
            accountAccessType       = 'CURRENT_ACCOUNT',
            authenticationProviders = ['AWS_SSO'],
            permissionType          = 'CUSTOMER_MANAGED',
            workspaceRoleArn        = role_arn,
            workspaceName           = name,
            workspaceDescription    = f'SG Playwright observability — {name}',
        )['workspace']['id']
        c.print(f'  [green]✓ AMG workspace kicked off[/]  {ws_id}  [dim](~2 min — runs while OpenSearch provisions)[/]')
        return ws_id
    except Exception as e:
        c.print(f'  [yellow]⚠ AMG creation failed:[/] {e}')
        c.print(f'    Create manually and run:  sp ob dashboard-import {name} --grafana-url <url>')
        return None


def _wait_amg_active(ws_id: str, r: str, c: Console) -> Optional[str]:
    """Poll until AMG workspace is ACTIVE. Returns endpoint or None."""
    grafana = boto3.client('grafana', region_name=r)
    for attempt in range(24):
        desc   = grafana.describe_workspace(workspaceId=ws_id)['workspace']
        status = desc.get('status', '?')
        if status == 'ACTIVE':
            ep = desc.get('endpoint', '')
            waited = f'{attempt * 15}s' if attempt else 'already active'
            c.print(f'  [green]✓ AMG ACTIVE[/]  https://{ep}  ({waited})')
            return ep
        if status in ('FAILED', 'DELETING', 'DELETED'):
            c.print(f'  [red]✗ AMG workspace {status}[/]')
            return None
        if attempt > 0:
            c.print(f'  [dim]  AMG {status}…  ({attempt * 15}s)[/]')
        time.sleep(15)
    c.print(f'  [yellow]⚠ AMG timed out — check AWS console[/]')
    return None


def _setup_amg_datasources(ws_id: str, endpoint: str, r: str,
                            amp_ws_id: str, os_endpoint: str, c: Console):
    """Add AMP + OpenSearch data sources to AMG and import the metrics dashboard."""
    grafana  = boto3.client('grafana', region_name=r)
    key_name = f'sg-setup-{int(time.time())}'
    try:
        api_key = grafana.create_workspace_api_key(
            keyName=key_name, keyRole='ADMIN', secondsToLive=300,
            workspaceId=ws_id)['key']
    except Exception as e:
        c.print(f'  [yellow]⚠ AMG API key creation failed:[/] {e}')
        return
    base    = f'https://{endpoint}'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    ds_name = 'Amazon Managed Service for Prometheus'
    try:
        amp_url = f'https://aps-workspaces.{r}.amazonaws.com/workspaces/{amp_ws_id}/'
        body    = {'name': ds_name, 'type': 'grafana-amazonprometheus-datasource',
                   'url': amp_url, 'access': 'proxy', 'isDefault': True,
                   'jsonData': {'httpMethod': 'POST', 'sigV4Auth': True,
                                'sigV4AuthType': 'workspace_iam_role', 'sigV4Region': r}}
        resp = requests.post(f'{base}/api/datasources', headers=headers, json=body, timeout=30)
        if resp.status_code in (200, 409):
            c.print(f'  [green]✓ AMP data source added[/]')
        else:
            c.print(f'  [yellow]⚠ AMP datasource HTTP {resp.status_code}:[/] {resp.text[:200]}')
        if os_endpoint:
            os_body = {'name': 'Amazon OpenSearch Service',
                       'type': 'grafana-opensearch-datasource',
                       'url': f'https://{os_endpoint}', 'access': 'proxy',
                       'jsonData': {'database': OPENSEARCH_INDEX, 'sigV4Auth': True,
                                    'sigV4AuthType': 'workspace_iam_role', 'sigV4Region': r,
                                    'timeField': '@timestamp', 'flavor': 'opensearch',
                                    'version': '2.3.0'}}
            resp2 = requests.post(f'{base}/api/datasources', headers=headers,
                                  json=os_body, timeout=30)
            if resp2.status_code in (200, 409):
                c.print(f'  [green]✓ OpenSearch data source added[/]')
            else:
                c.print(f'  [dim]  OpenSearch datasource HTTP {resp2.status_code}'
                        f' (known OS 3.x compat issue — use OpenSearch Dashboards for logs)[/]')
        dash_path = DASHBOARDS_DIR / 'grafana-sg-playwright-metrics.json'
        if dash_path.exists():
            payload = {'dashboard': json.loads(dash_path.read_text()), 'overwrite': True,
                       'inputs': [{'name': 'DS_AMP', 'type': 'datasource',
                                   'pluginId': 'grafana-amazonprometheus-datasource',
                                   'value': ds_name}]}
            dr = requests.post(f'{base}/api/dashboards/import', headers=headers,
                               json=payload, timeout=30)
            if dr.status_code < 300:
                c.print(f'  [green]✓ Grafana dashboard imported[/]')
            else:
                c.print(f'  [yellow]⚠ Dashboard import HTTP {dr.status_code}:[/] {dr.text[:200]}')
    finally:
        try:
            grafana.delete_workspace_api_key(keyName=key_name, workspaceId=ws_id)
        except Exception:
            pass


# ── create ─────────────────────────────────────────────────────────────────────

def _cmd_create_inner(name, r, account, amp, osc, no_wait, no_import, c,
                       admin_user='', admin_pass='', no_grafana=False):
    c.print(f'\n  [bold]Creating:[/] {name!r}  [dim]({r} / {account})[/]\n')

    # ── AMP ────────────────────────────────────────────────────────────────
    existing_ws = amp.list_workspaces(alias=name).get('workspaces', [])
    if existing_ws:
        ws_id = existing_ws[0]['workspaceId']
        c.print(f'  [yellow]AMP workspace exists[/]  {ws_id}')
    else:
        ws_id = amp.create_workspace(alias=name)['workspaceId']
        c.print(f'  [green]✓ AMP workspace created[/]  {ws_id}')
    amp_rw = _amp_rw_url({'workspaceId': ws_id}, r)
    c.print(f'  [dim]  export AMP_REMOTE_WRITE_URL="{amp_rw}"[/]')

    # ── OpenSearch ─────────────────────────────────────────────────────────
    master_password = None
    try:
        osc.describe_domain(DomainName=name)
        c.print(f'  [yellow]OpenSearch domain exists[/]  {name}')
    except osc.exceptions.ResourceNotFoundException:  # domain doesn't exist yet — create it
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
        c.print(f'\n  [bold yellow]Master password (printed once — save now):[/]')
        c.print(f'    export OB_OS_ADMIN_USER=admin')
        c.print(f'    export OB_OS_ADMIN_PASS="{master_password}"\n')

    # ── Kick off AMG now (parallel with OpenSearch ~15 min wait) ──────────
    amg_ws_id = None
    if not no_grafana and not no_wait:
        c.print(f'\n  [bold]Grafana (AMG)[/] — starting in parallel with OpenSearch\n')
        amg_ws_id = _start_amg_workspace(name, r, account, c)
        if amg_ws_id:
            _amg_url = f'https://{amg_ws_id}.grafana-workspace.{r}.amazonaws.com'
            c.print(f'  [dim]  export GRAFANA_WORKSPACE_URL="{_amg_url}"[/]')

    if no_wait:
        c.print('  [dim]--no-wait: use ob wait or ob info to track status.[/]\n')
        return

    # ── Wait for OpenSearch (long) ─────────────────────────────────────────
    _wait_active(amp, osc, ws_id, name, c)

    # ── Resolve + verify admin credentials ────────────────────────────────
    ep = _os_endpoint(osc.describe_domain(DomainName=name)['DomainStatus'])
    if ep:
        c.print(f'  [dim]  export OPENSEARCH_ENDPOINT="{ep}"[/]')
        c.print(f'  [dim]  Dashboards: https://{ep}/_dashboards/[/]')
    # master_password (freshly generated this run) always takes priority — it is
    # guaranteed correct. env-var overrides are only used on re-runs (master_password=None).
    if master_password:
        eff_user, eff_pass = 'admin', master_password
    else:
        eff_user, eff_pass = admin_user, admin_pass

    if not eff_user and ep:
        c.print('  [yellow]⚠ No admin credentials — skipping role mapping and dashboard import.[/]')
        c.print(f'    export OB_OS_ADMIN_USER=admin')
        c.print(f'    export OB_OS_ADMIN_PASS="<your-master-password>"')
        c.print(f'    sp ob create {name}')

    if eff_user and ep:
        # Pre-check credentials before making changes
        probe = requests.get(f'https://{ep}/', auth=(eff_user, eff_pass), timeout=15)
        if probe.status_code == 401:
            c.print(f'\n  [red]✗ Admin credentials rejected (401).[/]')
            c.print(f'    The username/password for [bold]{ep}[/] is incorrect.')
            c.print(f'\n  Fix, then re-run (idempotent):')
            c.print(f'    export OB_OS_ADMIN_USER=admin')
            c.print(f'    export OB_OS_ADMIN_PASS="<correct-password>"')
            c.print(f'    sp ob create {name}\n')
            return

    # ── Backend role mapping ───────────────────────────────────────────────
    if eff_user and ep:
        ec2_role = f'arn:aws:iam::{account}:role/{IAM_ROLE_NAME}'
        _map_backend_role(ep, ec2_role, eff_user, eff_pass, c)
        # Explicitly add admin user to all_access users list so Dashboards grants
        # tenant selection (OS 3.x doesn't auto-grant tenant access to master user)
        _map_admin_user(ep, eff_user, eff_pass, c)

    # ── OpenSearch saved-objects import ────────────────────────────────────
    if not no_import and ep:
        if not eff_user:
            c.print('  [yellow]⚠ No admin credentials for dashboard import.[/]')
            c.print('    Set OB_OS_ADMIN_USER / OB_OS_ADMIN_PASS or pass --admin-user / --admin-pass')
            c.print('    then run:  sp ob dashboard-import ' + name)
        else:
            ok = _do_import_os_saved_objects(ep, r, c, admin_user=eff_user, admin_pass=eff_pass)
            if not ok:
                c.print('  [red]Stopping — fix OS import error above before continuing.[/]\n')
                c.print(f'  Re-run: sp ob create {name} (command is idempotent)\n')
                return

    # ── Grafana (AMG) — wait for workspace kicked off earlier ─────────────
    grafana_url = ''
    if not no_grafana:
        if not amg_ws_id:
            # --no-wait path or late start: kick off now
            amg_ws_id = _start_amg_workspace(name, r, account, c)
        if amg_ws_id:
            c.print(f'\n  [bold]Grafana (AMG)[/] — waiting for ACTIVE\n')
        grafana_ep = _wait_amg_active(amg_ws_id, r, c) if amg_ws_id else None
        if amg_ws_id and grafana_ep:
            grafana_url = f'https://{grafana_ep}'
            # Map Grafana service role in OpenSearch so AMG can read logs
            if eff_user and ep:
                grafana_client = boto3.client('grafana', region_name=r)
                try:
                    gws_desc = grafana_client.describe_workspace(workspaceId=amg_ws_id)['workspace']
                    g_role   = gws_desc.get('workspaceRoleArn', '')
                    if g_role:
                        _map_backend_role(ep, g_role, eff_user, eff_pass, c)
                except Exception:
                    pass
            _setup_amg_datasources(amg_ws_id, grafana_ep, r, ws_id, ep, c)

    # ── Summary ────────────────────────────────────────────────────────────
    c.print(f'\n  [bold]Env exports for sp create:[/]')
    c.print(f'    export AMP_REMOTE_WRITE_URL="{_amp_rw_url({"workspaceId": ws_id}, r)}"')
    c.print(f'    export OPENSEARCH_ENDPOINT="{ep}"')
    if ep:
        c.print(f'    # Dashboards: https://{ep}/_dashboards/')
    if grafana_url:
        c.print(f'    export GRAFANA_WORKSPACE_URL="{grafana_url}"')
    c.print()


@app.command('create')
def cmd_create(
    name       : str           = typer.Argument(..., help='Stack name — becomes AMP alias and OpenSearch domain name.'),
    region     : Optional[str] = typer.Option(None, '--region'),
    no_wait    : bool          = typer.Option(False, '--no-wait',    help='Return immediately; use ob wait later.'),
    no_import  : bool          = typer.Option(False, '--no-import',  help='Skip auto-importing dashboards.'),
    no_grafana : bool          = typer.Option(False, '--no-grafana', help='Skip AMG workspace creation.'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER',
                                              help='OpenSearch admin username for dashboard import on re-runs.'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS',
                                              help='OpenSearch admin password for dashboard import on re-runs.'),
):
    """Create a full observability stack: AMP + OpenSearch + Grafana (AMG)."""
    r       = region or _region()
    account = _account()
    c       = Console(highlight=False)
    amp     = boto3.client('amp',        region_name=r)
    osc     = boto3.client('opensearch', region_name=r)
    try:
        _cmd_create_inner(name, r, account, amp, osc, no_wait, no_import, c,
                          admin_user=admin_user, admin_pass=admin_pass, no_grafana=no_grafana)
    except Exception as exc:
        if 'AccessDeniedException' in type(exc).__name__ or 'AccessDenied' in str(exc):
            c.print(f'\n  [red]AccessDenied:[/] {exc}\n')
            c.print('  Add the [bold]sg-playwright-observability[/] inline policy to SG-Deploy-User.')
            c.print('  See: library/docs/ops/v0.1.72__observability-platform.md\n')
            c.print('  Once permissions are fixed, re-run the same command — it is idempotent.\n')
            raise typer.Exit(1)
        raise


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
    amg_ws   = _amg_workspaces(r)
    has_amg  = stack_name in amg_ws
    if not yes:
        c.print(f'\n  [bold red]Permanently deletes:[/]')
        c.print(f'  • AMP workspace      alias={stack_name!r}')
        c.print(f'  • OpenSearch domain  name={stack_name!r}  (all log data)')
        if has_amg:
            c.print(f'  • AMG workspace      name={stack_name!r}')
        if not typer.confirm('\n  Confirm?', default=False):
            raise typer.Exit(0)
    c.print()
    amp     = boto3.client('amp',        region_name=r)
    osc     = boto3.client('opensearch', region_name=r)
    grafana = boto3.client('grafana',    region_name=r)
    for ws in amp.list_workspaces(alias=stack_name).get('workspaces', []):
        amp.delete_workspace(workspaceId=ws['workspaceId'])
        c.print(f'  [green]✓ AMP workspace deleted[/]  {ws["workspaceId"]}')
    try:
        osc.delete_domain(DomainName=stack_name)
        c.print(f'  [green]✓ OpenSearch deletion started[/]  (~10 min to complete)')
    except osc.exceptions.ResourceNotFoundException:
        c.print(f'  [dim]OpenSearch domain {stack_name!r} not found[/]')
    if has_amg:
        gws_id = amg_ws[stack_name]['id']
        try:
            grafana.delete_workspace(workspaceId=gws_id)
            c.print(f'  [green]✓ AMG workspace deleted[/]  {gws_id}')
        except Exception as e:
            c.print(f'  [yellow]⚠ AMG deletion failed:[/] {e}')
    c.print()


# ── Dashboard helpers ──────────────────────────────────────────────────────────

def _verify_index_pattern_exists(base: str, hdrs: dict, auth) -> bool:
    """Return True only if the saved object is readable AND has the right title.

    Checks the response body — not just the HTTP status — to catch AWS
    OpenSearch versions that return 200 on creation but don't persist.
    """
    r = requests.get(f'{base}/api/saved_objects/index-pattern/{OPENSEARCH_INDEX}',
                     headers=hdrs, auth=auth, timeout=15)
    if r.status_code >= 300:
        return False
    try:
        return r.json().get('attributes', {}).get('title') == OPENSEARCH_INDEX
    except (ValueError, AttributeError):
        return False


def _do_import_os_saved_objects(endpoint: str, region: str, c: Console,
                                 ndjson_path: Optional[Path] = None,
                                 admin_user: str = '', admin_pass: str = ''):
    """Create index pattern + import dashboards using admin basic-auth.

    Requires admin_user / admin_pass — IAM / SigV4 cannot write saved objects
    on AWS-managed OpenSearch with FGAC + system-index restriction enabled.
    Callers should abort before reaching here if credentials are missing.
    """
    auth = (admin_user, admin_pass)
    hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true', 'securitytenant': 'global'}
    base = f'https://{endpoint}/_dashboards'

    # ── Index pattern ───────────────────────────────────────────────────────────
    # Do NOT include 'fields' in the POST body — AOS returns HTTP 400
    # ("definition for this key is missing") whether fields is empty or populated.
    # OSD auto-discovers fields from the index mapping after the pattern is saved.
    # (Confirmed: working curl sends only title + timeFieldName.)
    ip_body = {'attributes': {'title': OPENSEARCH_INDEX, 'timeFieldName': '@timestamp'}}
    url = (f'{base}/api/saved_objects/index-pattern/{OPENSEARCH_INDEX}'
           f'?overwrite=true&security_tenant=global')
    resp = requests.post(url, json=ip_body, headers=hdrs, auth=auth, timeout=30)
    c.print(f'  [dim]  POST index-pattern: HTTP {resp.status_code}  '
            f'{resp.text[:200].strip()}[/]')

    dv_ok = _verify_index_pattern_exists(base, hdrs, auth)
    if dv_ok:
        c.print(f'  [green]✓ Index pattern created[/]  ({OPENSEARCH_INDEX})')
    else:
        c.print(f'  [red]✗ Index pattern creation failed (HTTP {resp.status_code})[/]')
        c.print(f'    Response: {resp.text[:400]}')
        c.print(f'    Check admin credentials and that the domain has FGAC enabled.')

    # ── Visualizations + dashboard ───────────────────────────────────────────────
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


def _check_os_dashboards(endpoint: str, region: str, c: Console,
                          admin_user: str = '', admin_pass: str = '') -> bool:
    """Verify index patterns and saved objects are visible in OpenSearch Dashboards.

    Queries both the Dashboards REST API and the system index directly, across
    the global and private tenants, so we can pinpoint tenant-mismatch issues.
    Returns True if the expected index pattern is visible in at least one tenant.
    """
    auth = (admin_user, admin_pass) if admin_user else None
    base = f'https://{endpoint}/_dashboards'

    c.print(f'\n  [bold]OpenSearch Dashboards health check[/]\n')

    # ── 1. Check Dashboards API across tenants ──────────────────────────────────
    found_tenants = []
    for tenant in ('global', 'private', '__user__'):
        hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true',
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

    # ── 2. Check saved objects (dashboards + visualizations) ───────────────────
    hdrs_global = {'Content-Type': 'application/json', 'osd-xsrf': 'true',
                   'securitytenant': 'global'}
    for obj_type in ('dashboard', 'visualization'):
        try:
            resp = requests.get(f'{base}/api/saved_objects/_find?type={obj_type}&per_page=100',
                                headers=hdrs_global, auth=auth, timeout=15)
        except Exception:
            continue
        if resp.status_code < 300:
            objs = resp.json().get('saved_objects', [])
            names = [o.get('attributes', {}).get('title', o.get('id', '?')) for o in objs]
            icon  = '[green]✓[/]' if names else '[yellow]—[/]'
            c.print(f'    {icon}  {obj_type}s (global):  {names or "(none)"}')

    # ── 3. System index direct read via SigV4 ─────────────────────────────────
    doc_id = f'index-pattern:{OPENSEARCH_INDEX}'
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

    # ── 4. Advice if tenant mismatch ───────────────────────────────────────────
    if sys_found and not found_tenants:
        c.print(f'\n  [yellow]⚠ Index pattern exists in the system index but is not '
                f'visible via any Dashboards tenant.[/]')
        c.print(f'    This usually means the doc was written to the system index but '
                f'Dashboards has not picked it up.')
        c.print(f'    Try: OS Dashboards → top-right avatar → Switch tenants → Global,')
        c.print(f'    then Stack Management → Index Patterns — check if it appears there.')
    elif found_tenants and 'global' not in found_tenants:
        c.print(f'\n  [yellow]⚠ Index pattern is in tenant(s) {found_tenants} but NOT '
                f'in [bold]global[/].[/]')
        c.print(f'    Switch to that tenant in the Dashboards UI to see it.')
    elif 'global' in found_tenants:
        c.print(f'\n  [green]✓ Index pattern visible in global tenant — '
                f'switch to Global in the Dashboards UI if you do not see it.[/]')

    c.print()
    return bool(found_tenants or sys_found)


# ── dashboard-import ───────────────────────────────────────────────────────────

@app.command('dashboard-import')
def cmd_dashboard_import(
    name        : Optional[str] = typer.Argument(None),
    region      : Optional[str] = typer.Option(None, '--region'),
    grafana_url : Optional[str] = typer.Option(None, '--grafana-url', envvar='GRAFANA_WORKSPACE_URL'),
    amp_ds      : str           = typer.Option('grafana-amazonprometheus-datasource', '--amp-datasource'),
    admin_user  : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER',
                                               help='OpenSearch master username.'),
    admin_pass  : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS',
                                               help='OpenSearch master password.'),
):
    """Import OpenSearch saved objects + Grafana dashboard from library/docs/ops/dashboards/.

    Requires --admin-user / --admin-pass (or OB_OS_ADMIN_USER / OB_OS_ADMIN_PASS env vars).
    IAM / SigV4 cannot write saved objects on AWS-managed OpenSearch with FGAC enabled.
    """
    if not admin_user or not admin_pass:
        typer.echo(
            '\nError: admin credentials required.\n'
            '  export OB_OS_ADMIN_USER=admin\n'
            '  export OB_OS_ADMIN_PASS="<master-password>"\n'
            '\n'
            'The master password was set when the OpenSearch domain was created.\n'
            'Retrieve it from AWS Secrets Manager if you do not have it locally.\n',
            err=True)
        raise typer.Exit(1)
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
    _check_os_dashboards(ep, r, c, admin_user=admin_user, admin_pass=admin_pass)
    c.print()


# ── dashboard-check ────────────────────────────────────────────────────────────

@app.command('dashboard-check')
def cmd_dashboard_check(
    name       : Optional[str] = typer.Argument(None),
    region     : Optional[str] = typer.Option(None, '--region'),
    admin_user : str           = typer.Option('', '--admin-user', envvar='OB_OS_ADMIN_USER'),
    admin_pass : str           = typer.Option('', '--admin-pass', envvar='OB_OS_ADMIN_PASS'),
):
    """Verify index patterns and saved objects are visible in OpenSearch Dashboards."""
    r          = region or _region()
    stack_name = _resolve_stack(name, r)
    by_name    = {s['name']: s for s in _list_stacks(r)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found or missing OpenSearch domain.', err=True)
        raise typer.Exit(1)
    ep = _os_endpoint(s['opensearch'])
    c  = Console(highlight=False)
    ok = _check_os_dashboards(ep, r, c, admin_user=admin_user, admin_pass=admin_pass)
    if not ok:
        raise typer.Exit(1)


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
