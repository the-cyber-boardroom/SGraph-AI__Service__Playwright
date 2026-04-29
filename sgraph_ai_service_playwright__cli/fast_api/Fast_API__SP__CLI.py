# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Fast_API__SP__CLI
# Stand-alone FastAPI app exposing the SP CLI management surface (EC2, Linux,
# Docker, Elastic, and observability) as HTTP routes.
# Extends osbot_fast_api.Fast_API — runs under uvicorn or behind Mangum (Lambda).
# Auth: X-API-Key middleware active when FAST_API__AUTH__API_KEY__VALUE is set.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi.staticfiles                                                            import StaticFiles
from mangum                                                                         import Mangum

from osbot_fast_api.api.Fast_API                                                    import Fast_API

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

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog  , service=self.catalog_service      )
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service       )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Elastic__Stack  , service=self.elastic_service      )
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service        )
        self.add_routes(Routes__Observability   , service=self.observability_service)
        self._mount_ui()

    def _mount_ui(self):                                                            # serve api_site/ at /ui — same origin eliminates CORS
        here     = os.path.dirname(__file__)
        ui_path  = os.path.abspath(os.path.join(here, '..', '..', 'sgraph_ai_service_playwright__api_site'))
        if os.path.isdir(ui_path):
            self.app().mount('/ui', StaticFiles(directory=ui_path, html=True), name='ui')
