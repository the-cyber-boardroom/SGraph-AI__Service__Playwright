# ═══════════════════════════════════════════════════════════════════════════════
# Waker — lambda_entry
# CANONICAL Lambda handler. Plain handler architecture — no FastAPI, no
# uvicorn, no LWA. Lambda Function URL passes the HTTP event directly; we
# parse it, route it, and return a Function-URL v2.0 response dict.
#
# (Fast_API__Waker.py exists in this package for completeness — it can be
# served locally via uvicorn for non-Lambda testing — but is NOT what runs
# in AWS. Any change to runtime behaviour must be made here.)
#
# Special routes handled directly (no slug resolution):
#   GET /__waker__/health  → plain JSON liveness check
#   GET /__waker__/deploy  → plain JSON dump of deploy metadata + schema fields
# Every other path goes through Waker__Handler.handle().
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import json
import os

from sg_compute_specs.vault_publish.waker.Slug__From_Host                        import Slug__From_Host
from sg_compute_specs.vault_publish.waker.Waker__Handler                         import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context


# ── Module-level deploy metadata (read once on cold start) ───────────────────

_vfile        = os.path.join(os.path.dirname(__file__), '..', 'version')
_FILE_VERSION = open(_vfile).read().strip() if os.path.isfile(_vfile) else 'unknown'
WAKER_VERSION = os.environ.get('WAKER_VERSION', _FILE_VERSION)

DEPLOY_INFO = {
    'service_version': os.environ.get('WAKER_SERVICE_VERSION', ''),
    'version'        : WAKER_VERSION,
    'deployed_at'    : os.environ.get('WAKER_DEPLOYED_AT',   ''),
    'deploy_id'      : os.environ.get('WAKER_DEPLOY_ID',     ''),
    'deploy_region'  : os.environ.get('WAKER_DEPLOY_REGION', ''),
    'deployed_by'    : os.environ.get('WAKER_DEPLOYED_BY',   ''),
    'git_commit'     : os.environ.get('WAKER_GIT_COMMIT',    ''),
}

# ── Header / event helpers (case-insensitive on event headers) ───────────────

def _h(headers: dict, name: str, default: str = '') -> str:
    lower = name.lower()
    for k, v in (headers or {}).items():
        if k.lower() == lower:
            return v if isinstance(v, str) else str(v)
    return default


def _viewer_host(headers: dict, origin_host: str) -> str:
    # Owned routing signal first (set by our CF Function on viewer-request),
    # then the standard proxy header, then the raw Host.
    for name in ('x-vault-viewer-host', 'x-forwarded-host'):
        v = _h(headers, name, '')
        if v:
            return v.split(',')[0].strip()
    return origin_host


def _source_ip(headers: dict, http_ctx: dict) -> str:
    xff = _h(headers, 'x-forwarded-for', '')
    if xff:
        return xff.split(',')[0].strip()
    return http_ctx.get('sourceIp', '') or ''


def _request_id(headers: dict, event: dict) -> str:
    for name in ('x-amzn-request-id', 'x-amzn-trace-id', 'x-amz-cf-id', 'x-request-id'):
        v = _h(headers, name, '')
        if v:
            return v
    return (event.get('requestContext') or {}).get('requestId', '') or ''


def _render_kv_block(items, default_missing: str = '(unset)') -> str:
    return '\n'.join(f'{k}: {v or default_missing}' for k, v in items)


def _render_event_meta(event: dict) -> str:
    # Lambda-event-equivalent of the ASGI scope: the bits that aren't headers
    # but tell you where the request came from at the AWS layer.
    ctx     = (event.get('requestContext') or {})
    http    = ctx.get('http', {}) or {}
    lines = [
        ('version'         , event.get('version', '')),
        ('rawPath'         , event.get('rawPath', '')),
        ('rawQueryString'  , event.get('rawQueryString', '')),
        ('method'          , http.get('method', '')),
        ('sourceIp'        , http.get('sourceIp', '')),
        ('userAgent'       , http.get('userAgent', '')),
        ('protocol'        , http.get('protocol', '')),
        ('requestContext.requestId', ctx.get('requestId', '')),
        ('requestContext.domainName', ctx.get('domainName', '')),
        ('requestContext.stage'    , ctx.get('stage', '')),
        ('requestContext.time'     , ctx.get('time', '')),
    ]
    return '\n'.join(f'{k}: {v}' for k, v in lines if v)


# ── Special routes (handled BEFORE slug resolution) ──────────────────────────

def _json_response(payload: dict, status: int = 200) -> dict:
    return {
        'statusCode'     : status,
        'headers'        : {'Content-Type': 'application/json'},
        'body'           : json.dumps(payload),
        'isBase64Encoded': False,
    }


def _route_special(path: str, qs_args: dict) -> dict:
    if path == '/__waker__/health':
        return _json_response({
            'status'         : 'ok',
            'service'        : 'vault-waker',
            'version'        : WAKER_VERSION,
            'service_version': DEPLOY_INFO['service_version'],
        })
    if path == '/__waker__/deploy':
        return _json_response({
            'service'    : 'vault-waker',
            'deploy_info': DEPLOY_INFO,
            'has_field'  : {
                # Smoke-check that the deployed Schema has the diagnostic
                # fields. If any are False, the schema deploy is older
                # than the lambda_entry that's running.
                'origin_host'      : 'origin_host'       in Schema__Waker__Request_Context.__annotations__,
                'forwarded_host'   : 'forwarded_host'    in Schema__Waker__Request_Context.__annotations__,
                'vault_viewer_host': 'vault_viewer_host' in Schema__Waker__Request_Context.__annotations__,
                'asgi_scope'       : 'asgi_scope'        in Schema__Waker__Request_Context.__annotations__,
                'deploy_info'      : 'deploy_info'       in Schema__Waker__Request_Context.__annotations__,
            },
        })
    if path == '/__waker__/cmd':
        if os.environ.get('WAKER_CMD_ENABLED', '1') not in ('1', 'true', 'yes'):
            return _json_response(
                {'error': 'WAKER_CMD_ENABLED is not set on this Lambda — debug RPC channel disabled'},
                status=403,
            )
        from sg_compute_specs.vault_publish.waker.Waker__Commands import dispatch
        cmd_name = qs_args.pop('name', '') if isinstance(qs_args, dict) else ''
        return _json_response(dispatch(cmd_name, qs_args or {}))
    return None


# ── Entry point ──────────────────────────────────────────────────────────────

def handler(event, context):                                                       # Lambda entry point
    headers     = event.get('headers') or {}
    origin_host = _h(headers, 'host', '')
    path        = event.get('rawPath', '/')
    raw_qs      = event.get('rawQueryString', '') or ''

    # Short-circuit reserved diagnostic paths so they don't go through slug
    # resolution. Useful for `setup lambda invoke` and external monitors.
    if path in ('/__waker__/health', '/__waker__/deploy', '/__waker__/cmd'):
        import urllib.parse
        qs_args = dict(urllib.parse.parse_qsl(raw_qs, keep_blank_values=True))
        return _route_special(path, qs_args)

    forwarded_host    = _h(headers, 'x-forwarded-host', '')
    vault_viewer_host = _h(headers, 'x-vault-viewer-host', '')
    viewer_host       = _viewer_host(headers, origin_host)
    slug              = Slug__From_Host().extract(viewer_host)
    raw_body          = event.get('body') or b''
    if isinstance(raw_body, str):
        raw_body = base64.b64decode(raw_body) if event.get('isBase64Encoded') else raw_body.encode()
    http_ctx = (event.get('requestContext') or {}).get('http', {})
    method   = http_ctx.get('method', 'GET')
    qs       = event.get('rawQueryString', '')
    full_path = path + ('?' + qs if qs else '')

    ctx = Schema__Waker__Request_Context(
        host              = viewer_host,
        origin_host       = origin_host,
        forwarded_host    = forwarded_host,
        vault_viewer_host = vault_viewer_host,
        slug              = str(slug) if slug else '',
        path              = full_path,
        method            = method,
        body              = raw_body if isinstance(raw_body, bytes) else raw_body.encode(),
        request_id        = _request_id(headers, event),
        source_ip         = _source_ip(headers, http_ctx),
        asgi_scope        = _render_event_meta(event),                              # Lambda event meta in place of an ASGI scope
        deploy_info       = _render_kv_block(DEPLOY_INFO.items()),
    )
    result = Waker__Handler(_version=WAKER_VERSION).handle(ctx)
    body   = result['body']
    return {
        'statusCode'     : result['status_code'],
        'headers'        : {k: v for k, v in result.get('headers', {}).items()
                            if k.lower() != 'content-length'},
        'body'           : body.decode() if isinstance(body, bytes) else body,
        'isBase64Encoded': False,
    }
