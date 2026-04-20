# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Routes__Web (mitmweb UI reverse-proxy)
#
# mitmweb runs bound to 127.0.0.1:8081 inside the container (NOT exposed on
# the security group). This route forwards GET /web/** to the local mitmweb
# so operators can view flows through the admin API's auth surface.
#
# WebSocket passthrough is deferred to Phase 2 — the HTTP UI is enough for
# Phase 1 read-only views.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                             import Request
from fastapi.responses                                                                   import Response
from osbot_fast_api.api.routes.Fast_API__Routes                                          import Fast_API__Routes
from osbot_utils.utils.Env                                                               import get_env

from agent_mitmproxy.consts                                                              import env_vars


TAG__ROUTES_WEB          = 'web'
DEFAULT_MITMWEB_HOST     = '127.0.0.1'
DEFAULT_MITMWEB_PORT     = 8081
STRIPPED_REQUEST_HEADERS = {'host', 'content-length'}                                    # Host misleads upstream; httpx sets its own content-length
HOP_BY_HOP_HEADERS       = {'content-length', 'transfer-encoding', 'connection', 'keep-alive'}


def _upstream_base_url() -> str:
    host = get_env(env_vars.ENV_VAR__MITMWEB_HOST) or DEFAULT_MITMWEB_HOST
    port = get_env(env_vars.ENV_VAR__MITMWEB_PORT) or DEFAULT_MITMWEB_PORT
    return f'http://{host}:{port}'


def _forward_headers(request: Request, api_key_header_name: str) -> dict:
    return {k: v for k, v in request.headers.items()
            if k.lower() not in STRIPPED_REQUEST_HEADERS
            and k.lower() != api_key_header_name.lower()}                                # Strip admin api key — mitmweb has no auth, doesn't need it


async def _proxy_to_mitmweb(request: Request, upstream_path: str, api_key_header_name: str) -> Response:
    import httpx

    upstream_url = f'{_upstream_base_url()}/{upstream_path}' if upstream_path else f'{_upstream_base_url()}/'
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(upstream_url,
                                    headers = _forward_headers(request, api_key_header_name),
                                    params  = request.query_params                           )

    passthrough_headers = {k: v for k, v in response.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}

    return Response(content     = response.content                    ,
                    status_code = response.status_code                ,
                    headers     = passthrough_headers                 ,
                    media_type  = response.headers.get('content-type'))


class Routes__Web(Fast_API__Routes):
    tag : str = TAG__ROUTES_WEB

    def setup_routes(self):                                                              # APIRouter-level registration — catch-all path param not supported by add_route_get's shape
        router              = self.router
        api_key_header_name = get_env(env_vars.ENV_VAR__API_KEY_NAME) or 'X-API-Key'

        @router.get('/')
        async def web_index(request: Request):
            return await _proxy_to_mitmweb(request, '', api_key_header_name)

        @router.get('/{path:path}')
        async def web_passthrough(request: Request, path: str):
            return await _proxy_to_mitmweb(request, path, api_key_header_name)
