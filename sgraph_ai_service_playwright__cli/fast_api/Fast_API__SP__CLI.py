# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Fast_API__SP__CLI
# Stand-alone FastAPI app exposing the SP CLI management surface (EC2, Linux,
# Docker, and observability) as HTTP routes.
#
# Extends osbot_fast_api.Fast_API (not Serverless__Fast_API) — the app is
# expected to run under uvicorn inside a container or on a local machine.
# A Lambda adapter can wrap this later without changing the app itself.
#
# Auth: inherits the X-API-Key middleware from osbot_fast_api when
# FAST_API__AUTH__API_KEY__VALUE is set. Unset = open for local development.
# ═══════════════════════════════════════════════════════════════════════════════

from mangum                                                                         import Mangum

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.docker.service.Docker__Service               import Docker__Service
from sgraph_ai_service_playwright__cli.docker.fast_api.routes.Routes__Docker__Stack import Routes__Docker__Stack
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                     import Ec2__Service
from sgraph_ai_service_playwright__cli.fast_api.exception_handlers                  import register_type_safe_handlers
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Ec2__Playwright      import Routes__Ec2__Playwright
from sgraph_ai_service_playwright__cli.fast_api.routes.Routes__Observability        import Routes__Observability
from sgraph_ai_service_playwright__cli.fast_api.runtime_version                     import resolve_version
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import Linux__Service
from sgraph_ai_service_playwright__cli.linux.fast_api.routes.Routes__Linux__Stack   import Routes__Linux__Stack
from sgraph_ai_service_playwright__cli.observability.service.Observability__Service import Observability__Service


class Fast_API__SP__CLI(Fast_API):
    docker_service        : Docker__Service                                         # Shared across all Routes__Docker__Stack requests; Type_Safe auto-initialises
    ec2_service           : Ec2__Service                                            # Shared across all Routes__Ec2 requests; Type_Safe auto-initialises
    linux_service         : Linux__Service                                          # Shared across all Routes__Linux__Stack requests; Type_Safe auto-initialises
    observability_service : Observability__Service                                  # Shared across all Routes__Observability requests

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.enable_api_key = True                                           # X-API-Key enforced when FAST_API__AUTH__API_KEY__VALUE is set; unset = open
        self.config.version        = resolve_version()                              # Surface the deployed SP CLI version on /docs + /openapi.json instead of osbot-fast-api's package version

    def setup(self):
        result = super().setup()
        register_type_safe_handlers(self.app())                                     # Maps osbot-fast-api's Type_Safe converter ValueError → 422 (instead of FastAPI's default 500)
        return result

    def handler(self):                                                              # Lambda handler — wraps the FastAPI app with Mangum. Same shape as Serverless__Fast_API.handler() so Agentic_Boot_Shim can call it without knowing this isn't a Serverless__Fast_API subclass.
        return Mangum(self.app(), lifespan='off')

    def setup_routes(self):
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service       )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service        )
        self.add_routes(Routes__Observability   , service=self.observability_service)
