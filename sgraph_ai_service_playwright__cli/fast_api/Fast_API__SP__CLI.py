# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Fast_API__SP__CLI
# Stand-alone FastAPI app exposing the SP CLI management surface as HTTP routes.
# Plugin routes are discovered from Plugin__Registry at startup; only the EC2
# and observability routes are wired manually (they are not plugin-owned).
# Auth: X-API-Key middleware active when FAST_API__AUTH__API_KEY__VALUE is set.
# /ui/* paths are exempt from API-key enforcement (browser navigation).
# ═══════════════════════════════════════════════════════════════════════════════

import sgraph_ai_service_playwright__api_site
from fastapi                                                                          import Request
from fastapi.staticfiles                                                              import StaticFiles
from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                          import Serverless__Fast_API
from starlette.responses                                                              import Response as StarletteResponse, RedirectResponse
from osbot_fast_api.api.middlewares.Middleware__Check_API_Key                         import Middleware__Check_API_Key
from sgraph_ai_service_playwright__cli.catalog.fast_api.routes.Routes__Stack__Catalog import Routes__Stack__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service        import Stack__Catalog__Service
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                   import Plugin__Registry, PLUGIN_FOLDERS
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                       import Ec2__Service
from sgraph_ai_service_playwright__cli.fast_api.exception_handlers                    import register_type_safe_handlers
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Ec2__Playwright        import Routes__Ec2__Playwright
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Observability          import Routes__Observability
from sgraph_ai_service_playwright__cli.fast_api.runtime_version                       import resolve_version
from sgraph_ai_service_playwright__cli.observability.service.Observability__Service   import Observability__Service


# ─── UI-bypass middleware ────────────────────────────────────────────────────
# Lets / and /ui/* through without API-key enforcement so browsers can load
# static pages.  All other paths use the normal key check.

class _Middleware__UI_Bypass(Middleware__Check_API_Key):
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        path = request.url.path
        if path == '/' or path.startswith('/ui'):
            return await call_next(request)
        return await super().dispatch(request, call_next)


class Fast_API__SP__CLI(Serverless__Fast_API):
    catalog_service       : Stack__Catalog__Service
    ec2_service           : Ec2__Service
    observability_service : Observability__Service
    plugin_registry       : Plugin__Registry

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.version = resolve_version()

    def setup(self):
        self.plugin_registry.plugin_folders = list(PLUGIN_FOLDERS)
        self.plugin_registry.discover().setup_all()
        self.catalog_service.plugin_registry = self.plugin_registry
        result = super().setup()
        register_type_safe_handlers(self.app())
        self.setup_ui()
        return result

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog , service=self.catalog_service      )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Observability   , service=self.observability_service)
        for routes_cls, svc in self.plugin_registry.route_service_pairs():
            self.add_routes(routes_cls, service=svc)

    def setup_ui(self):
        app = self.app()

        @app.get('/')
        async def _root():        return RedirectResponse('/ui/index.html')

        @app.get('/ui/admin')
        @app.get('/ui/admin/')
        async def _admin():       return RedirectResponse('/ui/admin/index.html')

        @app.get('/ui/user')
        @app.get('/ui/user/')
        async def _user():        return RedirectResponse('/ui/user/index.html')

        app.mount(path = '/ui'                                                       ,
                  app  = StaticFiles(directory=sgraph_ai_service_playwright__api_site.path, html=True),
                  name = 'ui'                                                        )
