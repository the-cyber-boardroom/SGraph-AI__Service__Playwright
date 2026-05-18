# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Fast_API__Waker
# Pure class — no import-time side effects. Initialised in lambda_entry.py.
# Exposes a single catch-all route that delegates every request to
# Waker__Handler. The host header drives slug resolution; paths are forwarded
# verbatim to the target vault-app.
#
# Debug context: request_id and source_ip are extracted from headers / the
# starlette client object so Waker__Handler can stamp them into X-Waker-*
# response headers and structured JSON logs.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi             import FastAPI, Request
from fastapi.responses   import Response

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.waker.Slug__From_Host                       import Slug__From_Host
from sg_compute_specs.vault_publish.waker.Waker__Handler                        import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context

_vfile = os.path.join(os.path.dirname(__file__), '..', 'version')
WAKER_VERSION = open(_vfile).read().strip() if os.path.isfile(_vfile) else 'unknown'


def _extract_request_id(request: Request) -> str:
    # LWA forwards Lambda's X-Amzn-Request-Id / X-Amzn-Trace-Id; CloudFront adds X-Amz-Cf-Id
    for hdr in ('x-amzn-request-id', 'x-amzn-trace-id', 'x-amz-cf-id', 'x-request-id'):
        v = request.headers.get(hdr)
        if v:
            return v
    return ''


def _extract_source_ip(request: Request) -> str:
    xff = request.headers.get('x-forwarded-for', '')
    if xff:
        return xff.split(',')[0].strip()
    client = getattr(request, 'client', None)
    return client.host if client else ''


# Headers we surface on the diagnostic page so operators can see what
# CloudFront / proxies are actually forwarding to the Lambda.
_PROXY_HEADER_SNIFF = (
    'x-forwarded-host', 'x-forwarded-for', 'x-forwarded-proto',
    'x-amz-cf-id', 'x-amzn-trace-id', 'x-amzn-request-id',
    'cloudfront-forwarded-proto', 'cloudfront-viewer-country',
    'cloudfront-viewer-address', 'via', 'referer',
)


def _render_proxy_headers(request: Request) -> str:
    lines = []
    for name in _PROXY_HEADER_SNIFF:
        v = request.headers.get(name)
        if v:
            lines.append(f'{name}: {v}')
    return '\n'.join(lines)


def _viewer_host(request: Request, origin_host: str) -> str:
    # CloudFront rewrites the Host header to the origin's hostname (Lambda URLs
    # reject mismatched Host). To recover the viewer's original host, we look
    # at X-Forwarded-Host first — this requires a CloudFront Function on the
    # viewer-request event that copies event.request.headers.host into a
    # custom X-Forwarded-Host header before CloudFront forwards to origin.
    xfh = request.headers.get('x-forwarded-host', '')
    if xfh:
        return xfh.split(',')[0].strip()
    return origin_host


class Fast_API__Waker(Type_Safe):

    def setup(self):
        return self

    def app(self) -> FastAPI:
        fast_app = FastAPI(title       = 'Vault Waker',
                           description = 'Subdomain-routing waker for vault-app stacks.',
                           version     = WAKER_VERSION,
                           docs_url    = '/__waker__/docs',
                           redoc_url   = None,
                           openapi_url = '/__waker__/openapi.json')
        self._register_routes(fast_app)
        return fast_app

    def _register_routes(self, fast_app: FastAPI):

        @fast_app.get('/__waker__/health', summary='Waker health probe (does not touch any vault).')
        async def health():
            return {'status': 'ok', 'service': 'vault-waker', 'version': WAKER_VERSION}

        @fast_app.api_route('/{path:path}',
                             methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        async def catch_all(request: Request, path: str):
            origin_host    = request.headers.get('host', '')
            forwarded_host = request.headers.get('x-forwarded-host', '')
            viewer_host    = _viewer_host(request, origin_host)
            slug           = Slug__From_Host().extract(viewer_host)
            body           = await request.body()
            ctx = Schema__Waker__Request_Context(
                host           = viewer_host,
                origin_host    = origin_host,
                forwarded_host = forwarded_host,
                slug           = str(slug) if slug else '',
                path           = '/' + path,
                method         = request.method,
                body           = body,
                request_id     = _extract_request_id(request),
                source_ip      = _extract_source_ip(request),
                proxy_headers  = _render_proxy_headers(request),
            )
            result = Waker__Handler(_version=WAKER_VERSION).handle(ctx)
            return Response(
                content    = result['body'],
                status_code= result['status_code'],
                headers    = {k: v for k, v in result.get('headers', {}).items()
                              if k.lower() != 'content-length'},
                media_type = result.get('headers', {}).get('Content-Type', 'text/html'),
            )
