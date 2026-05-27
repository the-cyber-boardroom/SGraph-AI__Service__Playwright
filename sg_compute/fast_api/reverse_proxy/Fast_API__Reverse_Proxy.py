# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__Reverse_Proxy
# Config-driven same-origin reverse proxy for any osbot-fast-api app.
#
# Reads one env var and mounts one forwarding router per entry:
#   FAST_API__REVERSE_PROXY__ROUTES = "pw=http://sg-playwright:8000[,mitm=http://...]"
#       comma-separated  <prefix>=<upstream_base_url>  entries; empty/unset → no-op.
#
# Each entry mounts at `/<prefix>/...` and forwards to `<upstream>/...` over the
# internal network. Same-origin with the host app → no mixed-content, no CORS.
#
# Auth translation: the inbound vault auth header/cookie (x-sgraph-access-token)
# is stripped; the upstream API key (X-API-Key) is injected from
# SGRAPH_SEND__ACCESS_TOKEN so the browser script needs to send nothing special.
#
# Generalised from sg_compute_specs/mitmproxy/api/routes/Routes__Web.py. Kept
# single-file and dependency-light (fastapi + httpx + osbot_utils only, all
# present in the sg-send-vault image) so it can be vendored into a container we
# do not build, exactly like Fast_API__TLS__Launcher. Destined for OSBot__Fast_API.
#
# A proxied route returns a raw Response (not .json() on a Type_Safe schema) —
# the same accepted exception used by Routes__Web and /browser/screenshot.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                            import APIRouter, Request
from fastapi.responses                  import Response
from osbot_utils.type_safe.Type_Safe    import Type_Safe

ENV_VAR__ROUTES   = 'FAST_API__REVERSE_PROXY__ROUTES'                               # "pw=http://sg-playwright:8000,mitm=http://agent-mitmproxy:8081"
ENV_VAR__TOKEN    = 'SGRAPH_SEND__ACCESS_TOKEN'                                     # injected upstream as X-API-Key
UPSTREAM_API_KEY  = 'X-API-Key'
ALL_METHODS       = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH']
STRIP_REQUEST     = {'host', 'content-length', 'x-sgraph-access-token', 'cookie'}   # never forwarded upstream
HOP_BY_HOP        = {'content-length', 'transfer-encoding', 'connection', 'keep-alive'}
TIMEOUT_SEC       = 120.0                                                           # > a long Playwright /sequence/execute run


class Fast_API__Reverse_Proxy(Type_Safe):

    def parse_routes(self) -> dict:                                                # {prefix: upstream_base_url}
        raw    = os.environ.get(ENV_VAR__ROUTES, '').strip()
        routes = {}
        for entry in (e for e in raw.split(',') if e.strip()):
            prefix, _, upstream = entry.partition('=')
            prefix   = prefix.strip().strip('/')
            upstream = upstream.strip().rstrip('/')
            if prefix and upstream:
                routes[prefix] = upstream
        return routes

    def mount(self, app) -> dict:                                                  # mount every configured route onto the app; returns what was mounted
        token  = os.environ.get(ENV_VAR__TOKEN, '')
        routes = self.parse_routes()
        for prefix, upstream in routes.items():
            self.mount_one(app, prefix, upstream, token)
        return routes

    def mount_one(self, app, prefix: str, upstream: str, token: str):
        router = APIRouter()

        async def proxy(request: Request, path: str = ''):
            import httpx
            url = f'{upstream}/{path}' if path else f'{upstream}/'
            if request.url.query:
                url = f'{url}?{request.url.query}'
            headers = {k: v for k, v in request.headers.items()
                       if k.lower() not in STRIP_REQUEST}
            if token:
                headers[UPSTREAM_API_KEY] = token                                  # vault auth → upstream auth
            headers['X-Forwarded-Prefix'] = f'/{prefix}'                           # Starlette upstreams honour this for correct self-URLs
            body = await request.body()
            async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
                response = await client.request(method  = request.method ,
                                                url     = url            ,
                                                headers = headers        ,
                                                content = body or None   )
            passthrough = {k: v for k, v in response.headers.items()
                           if k.lower() not in HOP_BY_HOP}
            return Response(content     = response.content                     ,
                            status_code = response.status_code                 ,
                            headers     = passthrough                          ,
                            media_type  = response.headers.get('content-type'))

        router.add_api_route('/',            proxy, methods=ALL_METHODS)
        router.add_api_route('/{path:path}', proxy, methods=ALL_METHODS)
        app.include_router(router, prefix=f'/{prefix}')
