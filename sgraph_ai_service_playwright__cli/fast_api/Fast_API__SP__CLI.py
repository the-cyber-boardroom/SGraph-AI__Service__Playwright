# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Fast_API__SP__CLI
# Stand-alone FastAPI app exposing the SP CLI management surface (EC2, Linux,
# Docker, Elastic, and observability) as HTTP routes.
# Extends osbot_fast_api.Fast_API — runs under uvicorn or behind Mangum (Lambda).
# Auth: X-API-Key middleware active when FAST_API__AUTH__API_KEY__VALUE is set.
# /ui/* paths are exempt from API-key enforcement (browser navigation).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                                                                        import Request
from fastapi.responses                                                              import RedirectResponse
from fastapi.staticfiles                                                            import StaticFiles
from mangum                                                                         import Mangum
from starlette.responses                                                            import Response as StarletteResponse

from osbot_fast_api.api.Fast_API                                                    import Fast_API
from osbot_fast_api.api.middlewares.Middleware__Check_API_Key                       import Middleware__Check_API_Key
from osbot_fast_api.api.schemas.consts.consts__Fast_API                             import (ENV_VAR__FAST_API__AUTH__API_KEY__NAME,
                                                                                             ENV_VAR__FAST_API__AUTH__API_KEY__VALUE)

from sgraph_ai_service_playwright__cli.catalog.fast_api.routes.Routes__Stack__Catalog import Routes__Stack__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service               import Docker__Service
from sgraph_ai_service_playwright__cli.docker.fast_api.routes.Routes__Docker__Stack import Routes__Docker__Stack
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                     import Ec2__Service
from sgraph_ai_service_playwright__cli.elastic.fast_api.routes.Routes__Elastic__Stack import Routes__Elastic__Stack
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.fast_api.exception_handlers                  import register_type_safe_handlers
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Ec2__Playwright      import Routes__Ec2__Playwright
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Observability        import Routes__Observability
from sgraph_ai_service_playwright__cli.fast_api.runtime_version                     import resolve_version
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import Linux__Service
from sgraph_ai_service_playwright__cli.linux.fast_api.routes.Routes__Linux__Stack   import Routes__Linux__Stack
from sgraph_ai_service_playwright__cli.observability.service.Observability__Service import Observability__Service


# ─── UI-bypass middleware ────────────────────────────────────────────────────
# Lets / and /ui/* through without API-key enforcement so browsers can load
# static pages.  All other paths use the normal key check.

class _Middleware__UI_Bypass(Middleware__Check_API_Key):
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        path = request.url.path
        if path == '/' or path.startswith('/ui'):
            return await call_next(request)
        return await super().dispatch(request, call_next)


class Fast_API__SP__CLI(Fast_API):
    catalog_service       : Stack__Catalog__Service                                 # Shared across all Routes__Stack__Catalog requests; Type_Safe auto-initialises
    docker_service        : Docker__Service                                         # Shared across all Routes__Docker__Stack requests; Type_Safe auto-initialises
    ec2_service           : Ec2__Service                                            # Shared across all Routes__Ec2 requests; Type_Safe auto-initialises
    elastic_service       : Elastic__Service                                        # Shared across all Routes__Elastic__Stack requests; Type_Safe auto-initialises
    linux_service         : Linux__Service                                          # Shared across all Routes__Linux__Stack requests; Type_Safe auto-initialises
    observability_service : Observability__Service                                  # Shared across all Routes__Observability requests

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.enable_api_key = True                                           # X-API-Key enforced when FAST_API__AUTH__API_KEY__VALUE is set; unset = open
        self.config.version        = resolve_version()                              # Surface the deployed SP CLI version on /docs + /openapi.json instead of osbot-fast-api's package version

    def setup(self):
        self.linux_service .setup()                                                 # lazy aws_client init — must be called before routes handle requests
        self.docker_service.setup()                                                 # same lazy pattern
        result = super().setup()
        register_type_safe_handlers(self.app())                                     # Maps osbot-fast-api's Type_Safe converter ValueError → 422 (instead of FastAPI's default 500)
        return result

    def handler(self):                                                              # Lambda handler — wraps the FastAPI app with Mangum. Same shape as Serverless__Fast_API.handler() so Agentic_Boot_Shim can call it without knowing this isn't a Serverless__Fast_API subclass.
        return Mangum(self.app(), lifespan='off')

    def setup_add_root_route(self):                                                 # redirect / → /ui/ (overrides base-class redirect to /docs)
        def redirect_to_ui():
            return RedirectResponse(url='/ui/')
        self.app_router().get('/')(redirect_to_ui)

    def setup_middleware__api_key_check(self,                                      # use UI-bypass subclass so /ui/* loads without API key
            env_var__api_key_name  : str = ENV_VAR__FAST_API__AUTH__API_KEY__NAME ,
            env_var__api_key_value : str = ENV_VAR__FAST_API__AUTH__API_KEY__VALUE):
        if self.config.enable_api_key:
            self.app().add_middleware(_Middleware__UI_Bypass                   ,
                                      env_var__api_key__name  = env_var__api_key_name  ,
                                      env_var__api_key__value = env_var__api_key_value ,
                                      allow_cors              = self.config.enable_cors)
        return self

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog  , service=self.catalog_service      )
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service       )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Elastic__Stack  , service=self.elastic_service      )
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service        )
        self.add_routes(Routes__Observability   , service=self.observability_service)
        self._mount_ui()

    def _mount_ui(self):                                                            # serve api_site/ at /ui — same origin eliminates CORS
        task_root = os.environ.get('LAMBDA_TASK_ROOT')                              # Lambda always sets this; avoids __file__ resolution issues in compiled environments
        if task_root:
            ui_path = os.path.join(task_root, 'sgraph_ai_service_playwright__api_site')
        else:
            here    = os.path.dirname(os.path.abspath(__file__))
            ui_path = os.path.join(here, '..', '..', 'sgraph_ai_service_playwright__api_site')
        ui_path = os.path.abspath(ui_path)
        if os.path.isdir(ui_path):
            self.app().mount('/ui', StaticFiles(directory=ui_path, html=True), name='ui')
