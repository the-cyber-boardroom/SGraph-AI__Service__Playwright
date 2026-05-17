# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Fast_API__Waker
# Pure class — no import-time side effects. Initialised in lambda_entry.py.
# Exposes a single catch-all route that delegates every request to
# Waker__Handler. The host header drives slug resolution; paths are forwarded
# verbatim to the target vault-app.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi             import FastAPI, Request
from fastapi.responses   import Response

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.waker.Slug__From_Host                       import Slug__From_Host
from sg_compute_specs.vault_publish.waker.Waker__Handler                        import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context


class Fast_API__Waker(Type_Safe):

    def setup(self):
        return self

    def app(self) -> FastAPI:
        fast_app = FastAPI(title='Vault Waker', docs_url=None, redoc_url=None)
        self._register_routes(fast_app)
        return fast_app

    def _register_routes(self, fast_app: FastAPI):

        @fast_app.api_route('/{path:path}',
                             methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        async def catch_all(request: Request, path: str):
            host = request.headers.get('host', '')
            slug = Slug__From_Host().extract(host)
            body = await request.body()
            ctx  = Schema__Waker__Request_Context(
                host   = host,
                slug   = str(slug) if slug else '',
                path   = '/' + path,
                method = request.method,
                body   = body,
            )
            result = Waker__Handler().handle(ctx)
            return Response(
                content    = result['body'],
                status_code= result['status_code'],
                headers    = {k: v for k, v in result.get('headers', {}).items()
                              if k.lower() != 'content-length'},
                media_type = result.get('headers', {}).get('Content-Type', 'text/html'),
            )

        @fast_app.get('/health')
        async def health():
            return {'status': 'ok', 'service': 'vault-waker'}
