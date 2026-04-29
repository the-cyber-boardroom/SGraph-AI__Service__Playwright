# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Fast_API__SP__CLI
# Stand-alone FastAPI app exposing the SP CLI management surface (EC2, Linux,
# Docker, Elastic, and observability) as HTTP routes.
# Extends osbot_fast_api.Fast_API — runs under uvicorn or behind Mangum (Lambda).
# Auth: X-API-Key middleware active when FAST_API__AUTH__API_KEY__VALUE is set.
# /ui/* paths are exempt from API-key enforcement (browser navigation).
# ═══════════════════════════════════════════════════════════════════════════════

import sgraph_ai_service_playwright__api_site
from fastapi                                                                          import Request
from fastapi.staticfiles                                                              import StaticFiles
from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                          import Serverless__Fast_API
from starlette.responses                                                              import Response as StarletteResponse
from osbot_fast_api.api.middlewares.Middleware__Check_API_Key                         import Middleware__Check_API_Key
from sgraph_ai_service_playwright__cli.catalog.fast_api.routes.Routes__Stack__Catalog import Routes__Stack__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service        import Stack__Catalog__Service
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service                 import Docker__Service
from sgraph_ai_service_playwright__cli.docker.fast_api.routes.Routes__Docker__Stack   import Routes__Docker__Stack
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                       import Ec2__Service
from sgraph_ai_service_playwright__cli.elastic.fast_api.routes.Routes__Elastic__Stack import Routes__Elastic__Stack
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service               import Elastic__Service
from sgraph_ai_service_playwright__cli.fast_api.exception_handlers                    import register_type_safe_handlers
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Ec2__Playwright        import Routes__Ec2__Playwright
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Observability          import Routes__Observability
from sgraph_ai_service_playwright__cli.fast_api.runtime_version                       import resolve_version
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                   import Linux__Service
from sgraph_ai_service_playwright__cli.linux.fast_api.routes.Routes__Linux__Stack     import Routes__Linux__Stack
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
    catalog_service       : Stack__Catalog__Service                                 # Shared across all Routes__Stack__Catalog requests; Type_Safe auto-initialises
    docker_service        : Docker__Service                                         # Shared across all Routes__Docker__Stack requests; Type_Safe auto-initialises
    ec2_service           : Ec2__Service                                            # Shared across all Routes__Ec2 requests; Type_Safe auto-initialises
    elastic_service       : Elastic__Service                                        # Shared across all Routes__Elastic__Stack requests; Type_Safe auto-initialises
    linux_service         : Linux__Service                                          # Shared across all Routes__Linux__Stack requests; Type_Safe auto-initialises
    observability_service : Observability__Service                                  # Shared across all Routes__Observability requests

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.version        = resolve_version()                              # Surface the deployed SP CLI version on /docs + /openapi.json instead of osbot-fast-api's package version

    def setup(self):
        self.linux_service .setup()                                                 # lazy aws_client init — must be called before routes handle requests
        self.docker_service.setup()                                                 # same lazy pattern
        result = super().setup()
        register_type_safe_handlers(self.app())                                     # Maps osbot-fast-api's Type_Safe converter ValueError → 422 (instead of FastAPI's default 500)
        self.catalog_service.linux_service   = self.linux_service                  # share initialised instances — catalog_service's own copies are never setup()
        self.catalog_service.docker_service  = self.docker_service
        self.catalog_service.elastic_service = self.elastic_service
        self.setup_ui()
        return result

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog  , service=self.catalog_service      )
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service       )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Elastic__Stack  , service=self.elastic_service      )
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service        )
        self.add_routes(Routes__Observability   , service=self.observability_service)

    def setup_ui(self):
        path_static        = "/ui"
        path_name          = 'ui'
        path_static_folder = sgraph_ai_service_playwright__api_site.path
        self.app().mount(path = path_static                                         ,
                         app  = StaticFiles(directory=path_static_folder, html=True),
                         name = path_name                                           )
