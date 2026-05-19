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

from fastapi                       import FastAPI, Request
from fastapi.middleware.cors       import CORSMiddleware
from fastapi.responses             import Response

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.waker.Slug__From_Host                       import Slug__From_Host
from sg_compute_specs.vault_publish.waker.Waker__Handler                        import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context

_vfile = os.path.join(os.path.dirname(__file__), '..', 'version')
_FILE_VERSION = open(_vfile).read().strip() if os.path.isfile(_vfile) else 'unknown'
# Env-var WAKER_VERSION (set by Setup__Lambda at deploy time) takes precedence —
# it survives Lambda cold/warm starts and matches the deploy that was published.
WAKER_VERSION = os.environ.get('WAKER_VERSION', _FILE_VERSION)

DEPLOY_INFO = {
    'service_version': os.environ.get('WAKER_SERVICE_VERSION', ''),                    # repo-root canonical version
    'version'        : WAKER_VERSION,                                                  # vault-publish sub-package version
    'deployed_at'    : os.environ.get('WAKER_DEPLOYED_AT',   ''),
    'deploy_id'      : os.environ.get('WAKER_DEPLOY_ID',     ''),
    'deploy_region'  : os.environ.get('WAKER_DEPLOY_REGION', ''),
    'deployed_by'    : os.environ.get('WAKER_DEPLOYED_BY',   ''),
    'git_commit'     : os.environ.get('WAKER_GIT_COMMIT',    ''),
}


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
    'x-vault-viewer-host',                                          # owned routing signal set by the CF Function (preferred)
    'x-forwarded-host',                                             # standard proxy header (also set by the CF Function)
    'x-forwarded-for', 'x-forwarded-proto',
    'x-amz-cf-id', 'x-amzn-trace-id', 'x-amzn-request-id',
    'cloudfront-forwarded-proto', 'cloudfront-viewer-country',
    'cloudfront-viewer-address', 'via', 'referer',
    'x-waker-flow-id', 'x-waker-cf-timestamp', 'x-waker-cf-version', # set by our CF Function
)


def _render_proxy_headers(request: Request) -> str:
    lines = []
    for name in _PROXY_HEADER_SNIFF:
        v = request.headers.get(name)
        if v:
            lines.append(f'{name}: {v}')
    return '\n'.join(lines)


def _render_all_headers(request: Request) -> str:
    # Dump every header verbatim — Lambda Web Adapter, CloudFront, and the
    # browser together can hide several layers of rewriting; the dump tells
    # us exactly what arrived at FastAPI.
    return '\n'.join(f'{k}: {v}' for k, v in sorted(request.headers.items()))


def _render_request_json(request: Request, body: bytes) -> str:
    # Pretty-printed JSON dump of what the Lambda actually received. This is
    # the closest we can get to "the original Lambda event" — LWA translates
    # the event into an HTTP request before our code sees it, so we capture
    # the HTTP-level view (method, URL parts, headers, body).
    import json as _json
    url = request.url
    body_repr = ''
    if body:
        try:
            body_repr = body.decode('utf-8')
            if len(body_repr) > 4096:
                body_repr = body_repr[:4096] + f'… (truncated; total {len(body)} bytes)'
        except UnicodeDecodeError:
            body_repr = f'<binary, {len(body)} bytes — base64 prefix: ' \
                        + __import__('base64').b64encode(body[:128]).decode() + '…>'
    payload = {
        'method'      : request.method,
        'url'         : str(url),
        'scheme'      : url.scheme,
        'path'        : url.path,
        'query'       : url.query,
        'headers'     : dict(sorted(request.headers.items())),
        'cookies'     : dict(request.cookies),
        'client'      : (request.client.host + ':' + str(request.client.port)) if request.client else '',
        'body'        : body_repr,
        'body_bytes'  : len(body),
    }
    return _json.dumps(payload, indent=2, ensure_ascii=False)


def _render_scope(request: Request) -> str:
    # ASGI scope reveals what uvicorn/LWA think the request looks like:
    # the local server address, viewer client tuple, scheme, root_path,
    # raw path, and query string.
    scope = getattr(request, 'scope', {}) or {}
    interesting = ('type', 'http_version', 'scheme', 'method', 'root_path',
                   'path', 'raw_path', 'query_string', 'client', 'server')
    lines = []
    for k in interesting:
        if k in scope:
            v = scope[k]
            if isinstance(v, (bytes, bytearray)):
                try:    v = v.decode('utf-8', errors='replace')
                except Exception: pass
            lines.append(f'{k}: {v!r}')
    return '\n'.join(lines)


def _viewer_host(request: Request, origin_host: str) -> str:
    # CloudFront rewrites the Host header to the origin's hostname (Lambda URLs
    # reject mismatched Host). To recover the viewer's original host, our CF
    # Function (vault-publish-viewer-host) sets two headers on viewer-request:
    #   x-vault-viewer-host  — our owned routing signal (preferred)
    #   x-forwarded-host     — standard proxy header (backup / interop)
    # We prefer the owned one to remove any ambiguity with proxies upstream of
    # CloudFront that might also stamp x-forwarded-host.
    for name in ('x-vault-viewer-host', 'x-forwarded-host'):
        v = request.headers.get(name, '')
        if v:
            return v.split(',')[0].strip()
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
        # CORS allows the warming page (served from <slug>.aws.sg-labs.app) to
        # poll the Lambda Function URL cross-origin. Scope to the public zone
        # via regex so any subdomain of the configured zone is allowed but no
        # other origin can read the JSON status (which exposes slug + EC2 IP).
        # allow_credentials=True is needed because the admin UI carries an
        # API-key cookie scoped to *.<zone>. Origin-regex + credentials=True
        # requires explicit list (not '*'), so we use the regex form.
        # Middleware also auto-handles OPTIONS preflights — replaces the
        # manual /__waker__/probe OPTIONS handler we had.
        zone = os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        # Escape dots in zone for regex; allow http+https against any subdomain.
        zone_re = zone.replace('.', r'\.')
        fast_app.add_middleware(
            CORSMiddleware,
            allow_origin_regex = rf'https?://([a-z0-9-]+\.)*{zone_re}(:\d+)?',
            allow_credentials  = True,
            allow_methods      = ['GET', 'POST', 'OPTIONS'],
            allow_headers      = ['*'],
            expose_headers     = ['x-waker-state', 'x-waker-ec2-state',
                                   'x-waker-action', 'x-waker-elapsed-ms',
                                   'x-waker-host', 'x-waker-slug',
                                   'x-waker-instance-id', 'x-waker-request-id',
                                   'x-waker-version'],
            max_age            = 86400,
        )
        self._register_routes(fast_app)
        return fast_app

    def _register_routes(self, fast_app: FastAPI):

        @fast_app.get('/__waker__/health', summary='Waker health probe (does not touch any vault).')
        async def health():
            return {'status': 'ok', 'service': 'vault-waker', 'version': WAKER_VERSION}

        @fast_app.get('/__waker__/deploy', summary='Echo the Lambda deploy metadata so operators can verify which version is live.')
        async def deploy():
            return {
                'service'    : 'vault-waker',
                'deploy_info': DEPLOY_INFO,
                'has_field'  : {
                    # Smoke-check that the deployed Schema has the new fields.
                    # If any of these are False, the deploy is stale.
                    'origin_host'      : 'origin_host'       in Schema__Waker__Request_Context.__annotations__,
                    'forwarded_host'   : 'forwarded_host'    in Schema__Waker__Request_Context.__annotations__,
                    'vault_viewer_host': 'vault_viewer_host' in Schema__Waker__Request_Context.__annotations__,
                    'all_headers'      : 'all_headers'       in Schema__Waker__Request_Context.__annotations__,
                    'asgi_scope'       : 'asgi_scope'        in Schema__Waker__Request_Context.__annotations__,
                    'deploy_info'      : 'deploy_info'       in Schema__Waker__Request_Context.__annotations__,
                    'request_json'     : 'request_json'      in Schema__Waker__Request_Context.__annotations__,
                },
            }

        @fast_app.get('/__waker__/probe',
                       summary='JSON status probe (CORS-enabled). The warming page polls this cross-origin from the Lambda Function URL instead of polling the slug FQDN, so the slug FQDN keep-alive socket can idle out and the next navigation gets a fresh DNS lookup.')
        async def probe(slug: str = ''):
            import json as _json
            from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2
            from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State import Enum__Instance__State
            from sg_compute_specs.vault_publish.waker.Waker__Handler import health_probe

            # CORS Allow-Origin / preflight handled by CORSMiddleware on the
            # FastAPI app. We only need to set non-CORS response headers here.
            response_headers = {
                'Cache-Control'   : 'no-store',
                'X-Waker-Version' : WAKER_VERSION,
                'Content-Type'    : 'application/json',
            }
            if not slug:
                return Response(content=_json.dumps({'error': 'slug query param required'}),
                                status_code=400, headers=response_headers)

            resolution = Endpoint__Resolver__EC2().resolve(slug)
            state      = resolution.state
            if state == Enum__Instance__State.UNKNOWN:
                waker_state = 'not_found'
            elif (state == Enum__Instance__State.RUNNING
                  and resolution.vault_url
                  and health_probe(resolution.vault_url)):
                waker_state = 'proxied'
            else:
                waker_state = 'warming'

            payload = {
                'slug'        : slug,
                'waker_state' : waker_state,
                'ec2_state'   : str(state),
                'instance_id' : resolution.instance_id,
                'public_ip'   : resolution.public_ip,
                'region'      : resolution.region,
            }
            return Response(content=_json.dumps(payload), status_code=200, headers=response_headers)

        @fast_app.api_route('/{path:path}',
                             methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        async def catch_all(request: Request, path: str):
            origin_host       = request.headers.get('host', '')
            forwarded_host    = request.headers.get('x-forwarded-host', '')
            vault_viewer_host = request.headers.get('x-vault-viewer-host', '')
            viewer_host       = _viewer_host(request, origin_host)
            slug              = Slug__From_Host().extract(viewer_host)
            body              = await request.body()
            ctx = Schema__Waker__Request_Context(
                host              = viewer_host,
                origin_host       = origin_host,
                forwarded_host    = forwarded_host,
                vault_viewer_host = vault_viewer_host,
                slug              = str(slug) if slug else '',
                path              = '/' + path,
                method            = request.method,
                body              = body,
                request_id        = _extract_request_id(request),
                source_ip         = _extract_source_ip(request),
                proxy_headers     = _render_proxy_headers(request),
                all_headers       = _render_all_headers(request),
                asgi_scope        = _render_scope(request),
                request_json      = _render_request_json(request, body),
                deploy_info       = '\n'.join(f'{k}: {v or "(unset)"}' for k, v in DEPLOY_INFO.items()),
            )
            result = Waker__Handler(_version=WAKER_VERSION).handle(ctx)
            return Response(
                content    = result['body'],
                status_code= result['status_code'],
                headers    = {k: v for k, v in result.get('headers', {}).items()
                              if k.lower() != 'content-length'},
                media_type = result.get('headers', {}).get('Content-Type', 'text/html'),
            )
