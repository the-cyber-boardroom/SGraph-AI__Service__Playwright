# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — observability_utils.py
# Shared constants and utility functions for observability scripts.
# No typer app — pure logic, importable without side effects.
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

from osbot_aws.AWS_Config import AWS_Config

# ── Constants ──────────────────────────────────────────────────────────────────

OPENSEARCH_ENGINE    = 'OpenSearch_3.5'
OPENSEARCH_INSTANCE  = 't3.small.search'
OPENSEARCH_VOLUME_GB = 10
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


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _sigv4(method: str, url: str, region: str,
           body: bytes = b'', extra_headers: dict = None) -> requests.Response:
    """Sign and execute an HTTP request against OpenSearch (service='es')."""
    session = boto3.Session()
    creds   = session.get_credentials()
    headers = {'Content-Type': 'application/json', **(extra_headers or {})}
    req     = AWSRequest(method=method.upper(), url=url, data=body, headers=headers)
    SigV4Auth(creds, 'es', region).add_auth(req)
    return requests.request(method, url, data=body, headers=dict(req.headers), timeout=60)


def _os_req(method: str, url: str, region: str,
            body: bytes = b'', auth=None, extra_headers: dict = None) -> requests.Response:
    """HTTP to OpenSearch: basic auth when auth=(user, pass) provided, SigV4 otherwise."""
    if auth:
        headers = {'Content-Type': 'application/json', **(extra_headers or {})}
        return requests.request(method, url, data=body or None,
                                headers=headers, auth=auth, timeout=60)
    return _sigv4(method, url, region, body, extra_headers)


# ── Stack discovery ────────────────────────────────────────────────────────────

def _amp_workspaces(region: str) -> dict:
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
    amp_ws  = _amp_workspaces(region)
    os_doms = _os_domains(region)
    amg_ws  = _amg_workspaces(region)
    out     = []
    for name in sorted(set(amp_ws) | set(os_doms) | set(amg_ws)):
        out.append({'name': name, 'amp': amp_ws.get(name),
                    'opensearch': os_doms.get(name), 'grafana': amg_ws.get(name)})
    return out


def _resolve_stack(name: Optional[str], region: str) -> str:
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


def _os_resolve(name: Optional[str], region: str):
    """Resolve stack name → (endpoint, stack_name). Exits if not found."""
    stack_name = _resolve_stack(name, region)
    by_name    = {s['name']: s for s in _list_stacks(region)}
    s          = by_name.get(stack_name)
    if not s or not s['opensearch']:
        typer.echo(f'Stack {stack_name!r} not found or missing OpenSearch domain.', err=True)
        raise typer.Exit(1)
    return _os_endpoint(s['opensearch']), stack_name


# ── Domain helpers ─────────────────────────────────────────────────────────────

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
