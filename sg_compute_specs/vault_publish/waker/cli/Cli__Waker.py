# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish waker: Cli__Waker
# Typer app for `sg vp waker` debug / operator verbs.
#
#   fake-event  — print a sample Lambda Function URL v2.0 event (pure Python)
#   invoke      — invoke the waker Lambda with a synthetic event
#   inspect     — full diagnostic of one slug (SSM + EC2 + health probe)
#   info        — show Lambda function metadata
#   tail        — stream CloudWatch Logs (stub — Phase B2)
#   logs        — one-shot CloudWatch log dump (stub — Phase B2)
#   trace       — invoke + capture all debug info (stub — Phase B2)
#   query       — CloudWatch Insights query (stub — Phase B2)
#
# boto3 EXCEPTION: invoke + info use boto3.client('lambda') directly.
# No osbot-aws Lambda wrapper exists yet (Phase B2); once it does, migrate.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import uuid
from datetime import datetime, timezone

import typer
from rich.console import Console

from sg_compute_specs.vault_publish.service.Vault_Publish__Service import WAKER_LAMBDA_NAME

app = typer.Typer(name='waker', help='Waker Lambda debug and diagnostic verbs.', no_args_is_help=True)

_NOT_YET = '\n  [dim]⌛  Phase B2 — not yet implemented[/]\n'
_ZONE_FALLBACK = 'aws.sg-labs.app'


# ── fake-event ────────────────────────────────────────────────────────────────

@app.command(name='fake-event', help='Print a sample Lambda Function URL v2.0 event (for local replay).')
def fake_event(
    slug  : str = typer.Option('', '--slug',   '-s', help='Slug name (sets Host header)'),
    zone  : str = typer.Option('', '--zone',   '-z', help='DNS zone (default: $SG_AWS__DNS__DEFAULT_ZONE or aws.sg-labs.app)'),
    method: str = typer.Option('GET', '--method', '-m', help='HTTP method'),
    path  : str = typer.Option('/',   '--path',   '-p', help='Request path'),
):
    resolved_zone = zone or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', _ZONE_FALLBACK)
    host          = f'{slug}.{resolved_zone}' if slug else resolved_zone
    now           = datetime.now(timezone.utc)
    ts            = now.strftime('%d/%b/%Y:%H:%M:%S +0000')
    event         = {
        'version'       : '2.0',
        'rawPath'       : path,
        'rawQueryString': '',
        'headers'       : {
            'host'           : host,
            'user-agent'     : 'sg-vp-waker-fake-event/0.1',
            'x-forwarded-for': '127.0.0.1',
        },
        'requestContext': {
            'http'     : {'method': method, 'path': path, 'sourceIp': '127.0.0.1'},
            'requestId': f'fake-{uuid.uuid4().hex[:8]}',
            'time'     : ts,
        },
        'body'           : None,
        'isBase64Encoded': False,
    }
    print(json.dumps(event, indent=2))


# ── invoke ────────────────────────────────────────────────────────────────────

@app.command(name='invoke', help='Invoke the waker Lambda with a synthetic event and show X-Waker-* headers.')
def invoke(
    host       : str  = typer.Option(..., '--host', '-H', help='Host header (e.g. sara-cv.aws.sg-labs.app)'),
    method     : str  = typer.Option('GET', '--method', '-m', help='HTTP method'),
    path       : str  = typer.Option('/', '--path', '-p', help='Request path'),
    debug_token: str  = typer.Option('', '--debug-token', help='X-Waker-Debug token'),
    full       : bool = typer.Option(False, '--full', help='Print full response body'),
    region     : str  = typer.Option('eu-west-2', '--region', '-r'),
):
    import boto3                                                                    # EXCEPTION — see module header
    c       = Console(highlight=False)
    headers = {'host': host, 'user-agent': 'sg-vp-waker-invoke/0.1'}
    if debug_token:
        headers['x-waker-debug'] = debug_token
    now   = datetime.now(timezone.utc)
    event = {
        'version'       : '2.0',
        'rawPath'       : path,
        'rawQueryString': '',
        'headers'       : headers,
        'requestContext': {
            'http'     : {'method': method, 'path': path, 'sourceIp': '127.0.0.1'},
            'requestId': f'invoke-{uuid.uuid4().hex[:8]}',
            'time'     : now.strftime('%d/%b/%Y:%H:%M:%S +0000'),
        },
        'body'           : None,
        'isBase64Encoded': False,
    }
    c.print(f'\n  [yellow]→[/]  Invoking [bold]{WAKER_LAMBDA_NAME}[/]…')
    try:
        lam     = boto3.client('lambda', region_name=region)
        resp    = lam.invoke(
            FunctionName   = WAKER_LAMBDA_NAME,
            InvocationType = 'RequestResponse',
            Payload        = json.dumps(event).encode(),
        )
        payload = json.loads(resp['Payload'].read())
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)

    status = payload.get('statusCode', 0)
    hdrs   = payload.get('headers', {})
    body   = payload.get('body', '')
    c.print()
    c.print(f'  status: {status}')
    c.print('  headers:')
    for k, v in sorted(hdrs.items()):
        if k.lower().startswith('x-waker'):
            c.print(f'    [dim]{k}[/]: {v}')
    if full:
        c.print(f'  body:\n{body}')
    else:
        c.print(f'  body size: {len(body)} chars  [dim](pass --full to see body)[/]')
    c.print()


# ── inspect ───────────────────────────────────────────────────────────────────

@app.command(name='inspect', help='Full diagnostic of one registered slug (SSM + EC2 + health probe).')
def inspect(
    slug     : str  = typer.Argument(..., help='Slug to inspect'),
    region   : str  = typer.Option('eu-west-2', '--region', '-r'),
    no_health: bool = typer.Option(False, '--no-health', help='Skip vault-app health probe'),
    output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output'),
):
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2         import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State   import Enum__Instance__State
    c = Console(highlight=False)
    try:
        resolution = Endpoint__Resolver__EC2().resolve(slug)
    except Exception as exc:
        c.print(f'  [red]✗  resolve failed: {exc}[/]')
        raise typer.Exit(1)

    health_ok   = None
    health_status = None
    if (not no_health and resolution.vault_url
            and resolution.state == Enum__Instance__State.RUNNING):
        try:
            import urllib3
            resp = urllib3.PoolManager(
                timeout=urllib3.Timeout(connect=2, read=5)
            ).request('GET', resolution.vault_url.rstrip('/') + '/ui/#!/login',
                      preload_content=True)
            health_ok     = resp.status < 500
            health_status = resp.status
        except Exception:
            health_ok     = False
            health_status = None

    if output_json:
        out = {
            'slug'       : slug,
            'state'      : str(resolution.state),
            'instance_id': resolution.instance_id,
            'public_ip'  : resolution.public_ip,
            'vault_url'  : resolution.vault_url,
            'region'     : resolution.region,
            'health_ok'  : health_ok,
        }
        print(json.dumps(out, indent=2))
        if resolution.state == Enum__Instance__State.UNKNOWN:
            raise typer.Exit(1)
        return

    if resolution.state == Enum__Instance__State.UNKNOWN:
        c.print(f'\n  Slug: [bold]{slug}[/]  [red]✗ not found[/]')
        c.print('  Slug not registered or no matching EC2 instance.\n')
        raise typer.Exit(1)

    c.print(f'\n  Slug: [bold]{slug}[/]')
    c.print()
    c.print('  EC2 instance:')
    c.print(f'    InstanceId  {resolution.instance_id}')
    c.print(f'    State       {resolution.state}')
    c.print(f'    PublicIP    {resolution.public_ip or "(none)"}')
    c.print(f'    VaultURL    {resolution.vault_url or "(none)"}')
    c.print(f'    Region      {resolution.region}')

    if health_ok is not None:
        c.print()
        c.print('  Vault-app health probe:')
        sym = '[green]✓ healthy[/]' if health_ok else '[red]✗ unhealthy[/]'
        c.print(f'    Status      {health_status}  {sym}')

    is_healthy = (resolution.state == Enum__Instance__State.RUNNING and health_ok is not False)
    overall    = '[green]HEALTHY ✓[/]' if is_healthy else f'[yellow]{resolution.state}[/]'
    c.print(f'\n  Overall: {overall}\n')


# ── info ──────────────────────────────────────────────────────────────────────

@app.command(name='info', help='Show waker Lambda function configuration.')
def info(region: str = typer.Option('eu-west-2', '--region', '-r')):
    import boto3                                                                    # EXCEPTION — see module header
    c = Console(highlight=False)
    c.print(f'\n  Lambda function: [bold]{WAKER_LAMBDA_NAME}[/]')
    try:
        lam    = boto3.client('lambda', region_name=region)
        fn     = lam.get_function(FunctionName=WAKER_LAMBDA_NAME)
        config = fn.get('Configuration', {})
        try:
            url_cfg = lam.get_function_url_config(FunctionName=WAKER_LAMBDA_NAME)
            fn_url  = url_cfg.get('FunctionUrl', '(none)')
        except Exception:
            fn_url = '(not configured)'
    except Exception as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)

    c.print()
    c.print(f'  ARN            {config.get("FunctionArn", "")}')
    c.print(f'  Runtime        {config.get("Runtime", "")}')
    c.print(f'  Handler        {config.get("Handler", "")}')
    c.print(f'  Memory         {config.get("MemorySize", "")} MB')
    c.print(f'  Timeout        {config.get("Timeout", "")} s')
    c.print(f'  Last modified  {config.get("LastModified", "")}')
    c.print(f'  Role           {config.get("Role", "")}')
    c.print(f'  Function URL   {fn_url}')
    c.print()


# ── stubs (Phase B2) ──────────────────────────────────────────────────────────

@app.command(name='tail', help='Stream CloudWatch Logs from the waker (Phase B2).')
def tail():
    Console(highlight=False).print(_NOT_YET)


@app.command(name='logs', help='One-shot CloudWatch log dump (Phase B2).')
def logs():
    Console(highlight=False).print(_NOT_YET)


@app.command(name='trace', help='Invoke + capture all debug layers in one pass (Phase B2).')
def trace():
    Console(highlight=False).print(_NOT_YET)


@app.command(name='query', help='Run a CloudWatch Insights query (Phase B2).')
def query():
    Console(highlight=False).print(_NOT_YET)
