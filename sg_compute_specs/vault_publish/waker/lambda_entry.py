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
    if path == '/__waker__/console':
        if os.environ.get('WAKER_CMD_ENABLED', '1') not in ('1', 'true', 'yes'):
            return {
                'statusCode'     : 403,
                'headers'        : {'Content-Type': 'text/html; charset=utf-8'},
                'body'           : '<h1>Console disabled</h1><p>Set WAKER_CMD_ENABLED=1 on the function env.</p>',
                'isBase64Encoded': False,
            }
        from sg_compute_specs.vault_publish.waker.Waker__Console import CONSOLE_HTML
        return {
            'statusCode'     : 200,
            'headers'        : {'Content-Type'  : 'text/html; charset=utf-8',
                                'Cache-Control' : 'no-store'},
            'body'           : CONSOLE_HTML,
            'isBase64Encoded': False,
        }
    return None


def _route_status_page(slug_arg: str, headers: dict, event: dict, raw_body: bytes,
                       full_path: str, method: str, vault_viewer_host: str,
                       forwarded_host: str, origin_host: str) -> dict:
    """/__waker__/status?slug=<slug>: render the diagnostic page for a slug
    WITHOUT triggering resolve/wake. Used by the "View diagnostics" link on
    the warming page (and as a general "what does the waker see for this
    slug right now?" inspector)."""
    viewer_host = vault_viewer_host or forwarded_host or origin_host
    ctx = Schema__Waker__Request_Context(
        host              = viewer_host,
        origin_host       = origin_host,
        forwarded_host    = forwarded_host,
        vault_viewer_host = vault_viewer_host,
        slug              = slug_arg,
        path              = full_path,
        method            = method,
        body              = raw_body,
        request_id        = _request_id(headers, event),
        source_ip         = _source_ip(headers, (event.get('requestContext') or {}).get('http', {})),
        asgi_scope        = _render_event_meta(event),
        deploy_info       = _render_kv_block(DEPLOY_INFO.items()),
    )
    # Resolve to get current state for the chosen slug (without start/proxy).
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Waker__State  import Enum__Waker__State
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Waker__Action import Enum__Waker__Action
    from sg_compute_specs.vault_publish.waker.Waker__Handler              import _render_not_found_html, _inject_waker_headers
    resolution = Endpoint__Resolver__EC2().resolve(slug_arg) if slug_arg else None
    if resolution is None:
        from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution import Schema__Endpoint__Resolution
        resolution = Schema__Endpoint__Resolution()
    body = _render_not_found_html(
        ctx, resolution,
        Enum__Waker__State.NOT_FOUND, Enum__Waker__Action.RETURNED_404,
        0, WAKER_VERSION,
    )
    headers_out = {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}
    _inject_waker_headers(headers_out, ctx, Enum__Waker__State.NOT_FOUND,
                          Enum__Waker__Action.RETURNED_404, resolution, 0, WAKER_VERSION)
    return {
        'statusCode'     : 200,
        'headers'        : {k: v for k, v in headers_out.items() if k.lower() != 'content-length'},
        'body'           : body,
        'isBase64Encoded': False,
    }


# ── Entry point ──────────────────────────────────────────────────────────────

def handler(event, context):                                                       # Lambda entry point
    headers     = event.get('headers') or {}
    origin_host = _h(headers, 'host', '')
    path        = event.get('rawPath', '/')
    raw_qs      = event.get('rawQueryString', '') or ''

    # Short-circuit reserved diagnostic paths so they don't go through slug
    # resolution. Useful for `setup lambda invoke`, external monitors, and
    # the browser console (which calls /__waker__/cmd via fetch).
    if path in ('/__waker__/health', '/__waker__/deploy', '/__waker__/cmd', '/__waker__/console'):
        import urllib.parse
        qs_args = dict(urllib.parse.parse_qsl(raw_qs, keep_blank_values=True))
        return _route_special(path, qs_args)
    if path == '/__waker__/status':
        import urllib.parse
        qs_args = dict(urllib.parse.parse_qsl(raw_qs, keep_blank_values=True))
        slug_arg = qs_args.get('slug', '')
        http_ctx_status = (event.get('requestContext') or {}).get('http', {}) or {}
        raw_body_status = event.get('body') or b''
        if isinstance(raw_body_status, str):
            raw_body_status = base64.b64decode(raw_body_status) if event.get('isBase64Encoded') \
                else raw_body_status.encode()
        return _route_status_page(
            slug_arg          = slug_arg,
            headers           = headers,
            event             = event,
            raw_body          = raw_body_status,
            full_path         = path + ('?' + raw_qs if raw_qs else ''),
            method            = http_ctx_status.get('method', 'GET'),
            vault_viewer_host = _h(headers, 'x-vault-viewer-host', ''),
            forwarded_host    = _h(headers, 'x-forwarded-host', ''),
            origin_host       = origin_host,
        )

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
