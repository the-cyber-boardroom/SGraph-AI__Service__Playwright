# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish waker — Routes__Waker
# Root-mounted (tag='') route class for the edge router. Diagnostic surfaces are
# explicit paths; everything else falls through a catch-all that runs the slug
# resolve → wake → proxy state machine (Waker__Handler).
#
#   GET  /__waker__/health    JSON liveness check
#   GET  /__waker__/deploy    JSON deploy metadata + schema-field smoke check
#   GET  /__waker__/cmd       debug RPC channel        (gated by WAKER_CMD_ENABLED)
#   GET  /__waker__/console   debug console HTML       (gated by WAKER_CMD_ENABLED)
#   *    /__waker__/probe     JSON status probe + CORS (auth-free, warming pages)
#   GET  /__waker__/status    diagnostic HTML for a slug (no resolve/wake)
#   *    /{path:path}         slug router → Waker__Handler.handle()
#
# The catch-all is registered LAST so the explicit diagnostic paths (and the
# FastAPI-owned /docs, /openapi.json) win the route match. Mangum exposes the
# raw Lambda event at request.scope['aws.event'] — used for the event-meta
# debug block in place of the old hand-parsed event dict.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import re

from starlette.requests                         import Request
from starlette.responses                        import Response, JSONResponse, HTMLResponse
from osbot_fast_api.api.routes.Fast_API__Routes import Fast_API__Routes

from sg_compute_specs.vault_publish.lambdas.waker.Slug__From_Host                        import Slug__From_Host
from sg_compute_specs.vault_publish.lambdas.waker.Waker__Handler                         import Waker__Handler
from sg_compute_specs.vault_publish.lambdas.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context
from sg_compute_specs.vault_publish.lambdas.waker.waker__config                          import (
    WAKER_VERSION, DEPLOY_INFO, waker_zone)


ROUTES_PATHS__WAKER = ['/__waker__/health', '/__waker__/deploy', '/__waker__/cmd',
                       '/__waker__/console', '/__waker__/probe', '/__waker__/status',
                       '/{path:path}']


# ── request helpers (Starlette headers are already case-insensitive) ──────────

def _viewer_host(headers, origin_host: str) -> str:
    for name in ('x-vault-viewer-host', 'x-forwarded-host'):
        v = headers.get(name, '')
        if v:
            return v.split(',')[0].strip()
    return origin_host


def _source_ip(request: Request) -> str:
    xff = request.headers.get('x-forwarded-for', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.client.host if request.client else ''


def _request_id(request: Request) -> str:
    for name in ('x-amzn-request-id', 'x-amzn-trace-id', 'x-amz-cf-id', 'x-request-id'):
        v = request.headers.get(name, '')
        if v:
            return v
    event = request.scope.get('aws.event') or {}
    return (event.get('requestContext') or {}).get('requestId', '') or ''


def _render_kv_block(items, default_missing: str = '(unset)') -> str:
    return '\n'.join(f'{k}: {v or default_missing}' for k, v in items)


def _render_event_meta(request: Request) -> str:
    # Lambda-event-equivalent of the ASGI scope: the AWS-layer routing signals
    # that aren't headers. Sourced from the raw event Mangum stashed on the scope.
    event = request.scope.get('aws.event') or {}
    ctx   = event.get('requestContext') or {}
    http  = ctx.get('http', {}) or {}
    lines = [
        ('version'                  , event.get('version', '')),
        ('rawPath'                  , event.get('rawPath', '')),
        ('rawQueryString'           , event.get('rawQueryString', '')),
        ('method'                   , http.get('method', '')),
        ('sourceIp'                 , http.get('sourceIp', '')),
        ('userAgent'                , http.get('userAgent', '')),
        ('protocol'                 , http.get('protocol', '')),
        ('requestContext.requestId' , ctx.get('requestId', '')),
        ('requestContext.domainName', ctx.get('domainName', '')),
        ('requestContext.stage'     , ctx.get('stage', '')),
        ('requestContext.time'      , ctx.get('time', '')),
    ]
    return '\n'.join(f'{k}: {v}' for k, v in lines if v)


def _build_cors_headers(origin: str) -> dict:
    # Echo the request Origin back as Access-Control-Allow-Origin iff it matches
    # the configured zone (any subdomain). Same-zone-only is tighter than '*'
    # and required for allow_credentials=true; cross-zone origins get 'null'
    # which fails the browser's CORS check (intentional).
    zone    = waker_zone()
    pattern = rf'^https?://(?:[a-z0-9-]+\.)*{re.escape(zone)}(?::\d+)?$'
    allow   = origin if (origin and re.match(pattern, origin)) else 'null'
    return {
        'Access-Control-Allow-Origin'     : allow,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods'    : 'GET, OPTIONS',
        'Access-Control-Allow-Headers'    : 'content-type, x-vault-warming-probe',
        'Access-Control-Max-Age'          : '86400',
        'Vary'                            : 'Origin',
    }


class Routes__Waker(Fast_API__Routes):
    tag : str = ''                                                                   # root-mounted (no prefix)

    # ── diagnostics ───────────────────────────────────────────────────────────
    def health(self):
        return {'status'         : 'ok',
                'service'        : 'vault-waker',
                'version'        : WAKER_VERSION,
                'service_version': DEPLOY_INFO['service_version']}
    health.__route_path__ = '/__waker__/health'

    def deploy(self):
        return {'service'    : 'vault-waker',
                'deploy_info': DEPLOY_INFO,
                'has_field'  : {                                                     # smoke-check the deployed Schema carries the diagnostic fields
                    'origin_host'      : 'origin_host'       in Schema__Waker__Request_Context.__annotations__,
                    'forwarded_host'   : 'forwarded_host'    in Schema__Waker__Request_Context.__annotations__,
                    'vault_viewer_host': 'vault_viewer_host' in Schema__Waker__Request_Context.__annotations__,
                    'asgi_scope'       : 'asgi_scope'        in Schema__Waker__Request_Context.__annotations__,
                    'deploy_info'      : 'deploy_info'       in Schema__Waker__Request_Context.__annotations__,
                }}
    deploy.__route_path__ = '/__waker__/deploy'

    async def cmd(self, request: Request):
        if os.environ.get('WAKER_CMD_ENABLED', '1') not in ('1', 'true', 'yes'):
            return JSONResponse({'error': 'WAKER_CMD_ENABLED is not set on this Lambda — debug RPC channel disabled'},
                                status_code=403)
        from sg_compute_specs.vault_publish.lambdas.waker.Waker__Commands import dispatch
        args     = dict(request.query_params)
        cmd_name = args.pop('name', '')
        return JSONResponse(dispatch(cmd_name, args))
    cmd.__route_path__ = '/__waker__/cmd'

    async def console(self, request: Request):
        if os.environ.get('WAKER_CMD_ENABLED', '1') not in ('1', 'true', 'yes'):
            return HTMLResponse('<h1>Console disabled</h1><p>Set WAKER_CMD_ENABLED=1 on the function env.</p>',
                                status_code=403)
        from sg_compute_specs.vault_publish.lambdas.waker.Waker__Console import CONSOLE_HTML
        return HTMLResponse(CONSOLE_HTML, headers={'Cache-Control': 'no-store'})
    console.__route_path__ = '/__waker__/console'

    async def probe(self, request: Request):
        # /__waker__/probe?slug=X — JSON status snapshot used by warming pages
        # cross-origin. NO resolve/wake/proxy. CORS handled here (base CORS is
        # disabled so the zone-match + x-vault-warming-probe contract is exact).
        cors = _build_cors_headers(request.headers.get('origin', ''))
        if request.method.upper() == 'OPTIONS':
            return Response(status_code=204, headers=cors)

        headers = {**cors, 'Cache-Control': 'no-store', 'X-Waker-Version': WAKER_VERSION}
        slug    = request.query_params.get('slug', '')
        if not slug:
            return JSONResponse({'error': 'slug query param required'}, status_code=400, headers=headers)

        from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2       import Endpoint__Resolver__EC2
        from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Instance__State import Enum__Instance__State
        from sg_compute_specs.vault_publish.lambdas.waker.Waker__Handler                import health_probe

        resolution = Endpoint__Resolver__EC2().resolve(slug)
        state      = resolution.state
        if state == Enum__Instance__State.UNKNOWN:
            waker_state = 'not_found'
        elif state == Enum__Instance__State.RUNNING and resolution.vault_url and health_probe(resolution.vault_url):
            waker_state = 'proxied'
        else:
            waker_state = 'warming'
        payload = {'slug'        : slug,
                   'waker_state' : waker_state,
                   'ec2_state'   : str(state),
                   'instance_id' : resolution.instance_id,
                   'public_ip'   : resolution.public_ip,
                   'region'      : resolution.region}
        return JSONResponse(payload, headers=headers)
    probe.__route_path__ = '/__waker__/probe'

    async def status(self, request: Request):
        # /__waker__/status?slug=X — render the diagnostic page for a slug
        # WITHOUT resolve/wake. Used by the "View diagnostics" warming-page link.
        from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2          import Endpoint__Resolver__EC2
        from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Waker__State       import Enum__Waker__State
        from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Waker__Action      import Enum__Waker__Action
        from sg_compute_specs.vault_publish.lambdas.waker.schemas.Schema__Endpoint__Resolution import Schema__Endpoint__Resolution
        from sg_compute_specs.vault_publish.lambdas.waker.Waker__Handler                   import _render_not_found_html, _inject_waker_headers

        slug = request.query_params.get('slug', '')
        ctx  = self._build_ctx(request, slug_override=slug)
        resolution = Endpoint__Resolver__EC2().resolve(slug) if slug else Schema__Endpoint__Resolution()
        body = _render_not_found_html(ctx, resolution, Enum__Waker__State.NOT_FOUND,
                                      Enum__Waker__Action.RETURNED_404, 0, WAKER_VERSION)
        headers_out = {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}
        _inject_waker_headers(headers_out, ctx, Enum__Waker__State.NOT_FOUND,
                              Enum__Waker__Action.RETURNED_404, resolution, 0, WAKER_VERSION)
        headers_out = {k: v for k, v in headers_out.items() if k.lower() != 'content-length'}
        return HTMLResponse(body, headers=headers_out)
    status.__route_path__ = '/__waker__/status'

    # ── catch-all slug router ───────────────────────────────────────────────────
    async def slug_router(self, request: Request, path: str = ''):
        ctx    = await self._build_ctx_async(request)
        result = Waker__Handler(_version=WAKER_VERSION).handle(ctx)
        body   = result['body']
        headers = {k: v for k, v in result.get('headers', {}).items()
                   if k.lower() != 'content-length'}
        return Response(content=body, status_code=result['status_code'], headers=headers)

    # ── ctx builders ────────────────────────────────────────────────────────────
    def _build_ctx(self, request: Request, slug_override: str = None,
                   body: bytes = b'') -> Schema__Waker__Request_Context:
        headers           = request.headers
        origin_host       = headers.get('host', '')
        forwarded_host    = headers.get('x-forwarded-host', '')
        vault_viewer_host = headers.get('x-vault-viewer-host', '')
        viewer_host       = _viewer_host(headers, origin_host)
        if slug_override is not None:                                                # /__waker__/status passes an explicit slug
            slug = slug_override
        else:                                                                        # catch-all extracts slug from the viewer host
            extracted = Slug__From_Host().extract(viewer_host)
            slug      = str(extracted) if extracted else ''
        full_path         = request.url.path + ('?' + request.url.query if request.url.query else '')
        return Schema__Waker__Request_Context(
            host              = viewer_host,
            origin_host       = origin_host,
            forwarded_host    = forwarded_host,
            vault_viewer_host = vault_viewer_host,
            slug              = slug or '',
            path              = full_path,
            method            = request.method,
            body              = body,
            request_id        = _request_id(request),
            source_ip         = _source_ip(request),
            asgi_scope        = _render_event_meta(request),
            deploy_info       = _render_kv_block(DEPLOY_INFO.items()),
        )

    async def _build_ctx_async(self, request: Request) -> Schema__Waker__Request_Context:
        return self._build_ctx(request, slug_override=None, body=await request.body())

    def setup_routes(self):
        self.add_route_get(self.health)
        self.add_route_get(self.deploy)
        self.add_route_get(self.cmd)
        self.add_route_get(self.console)
        self.add_route_any(self.probe)
        self.add_route_get(self.status)
        self.add_route_any(self.slug_router, path='/{path:path}')                    # registered LAST — lowest match priority
