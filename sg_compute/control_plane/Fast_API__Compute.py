# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__Compute
# Control-plane FastAPI for the SG/Compute service.
#
# Auth model
# ──────────
# Base class: Serverless__Fast_API (enable_api_key=True by default).
# Middleware: _Middleware__Health_Bypass — forwards /api/health/* unauthenticated
# so load-balancer / Lambda health checks don't need credentials.
# All other routes require X-API-Key (or cookie) matching
# FAST_API__AUTH__API_KEY__VALUE.
#
# Boot assertion: setup_middlewares() raises AssertionError if the env var is
# unset or shorter than 16 chars. Fail-loud; never fail-open.
#
# Auth-free paths (no X-API-Key required):
#   /api/health        — ping
#   /api/health/ready  — readiness probe
#   /docs              — Swagger UI  (AUTH__EXCLUDED_PATHS in middleware)
#   /openapi.json      — OpenAPI spec
#
# Mounted routes
# ──────────────
#   /api/health                   Routes__Compute__Health   (ping + readiness)
#   /api/specs                    Routes__Compute__Specs    (catalogue + per-spec info)
#   /api/nodes                    Routes__Compute__Nodes    (cross-spec node list)
#   /api/stacks                   Routes__Compute__Stacks   (cross-spec stack list)
#   /api/vault                    Routes__Vault__Spec       (per-spec vault write/list/delete)
#   /ui/*                         StaticFiles               (dashboard shared assets — sgraph_ai_service_playwright__api_site/)
#   /api/specs/{spec_id}/ui/*     StaticFiles               (spec UI assets — mounted when ui/ exists)
#   /api/specs/{spec_id}/*        per-spec Routes__*__Stack (discovered by convention)
#   /legacy/*                     Fast_API__SP__CLI sub-app (deprecated; X-Deprecated header on all responses)
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                                                                  import Request
from fastapi.responses                                                        import JSONResponse
from osbot_fast_api.api.middlewares.Middleware__Check_API_Key                 import Middleware__Check_API_Key
from osbot_fast_api.api.schemas.consts.consts__Fast_API                      import (ENV_VAR__FAST_API__AUTH__API_KEY__NAME ,
                                                                                      ENV_VAR__FAST_API__AUTH__API_KEY__VALUE)
from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                  import Serverless__Fast_API

from sg_compute.control_plane.Spec__Routes__Loader                           import Spec__Routes__Loader
from sg_compute.control_plane.routes.Routes__Compute__AMIs                   import Routes__Compute__AMIs
from sg_compute.control_plane.routes.Routes__Compute__Health                 import Routes__Compute__Health
from sg_compute.control_plane.routes.Routes__Compute__Nodes                  import Routes__Compute__Nodes
from sg_compute.control_plane.routes.Routes__Compute__Pods                   import Routes__Compute__Pods
from sg_compute.control_plane.routes.Routes__Compute__Specs                  import Routes__Compute__Specs
from sg_compute.control_plane.routes.Routes__Compute__Stacks                 import Routes__Compute__Stacks
from sg_compute.core.pod.Pod__Manager                                        import Pod__Manager
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.platforms.exceptions.Exception__AWS__No_Credentials          import Exception__AWS__No_Credentials
from sg_compute.vault.api.routes.Routes__Vault__Spec                         import Routes__Vault__Spec
from sg_compute.vault.service.Vault__Spec__Writer                            import Vault__Spec__Writer

_AUTH_FREE_PATHS = {'/api/health', '/api/health/ready'}                        # load-balancer / Lambda probes; no X-API-Key required


class _Middleware__Health_Bypass(Middleware__Check_API_Key):                   # Auth-free exemption for health probes
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _AUTH_FREE_PATHS:
            return await call_next(request)
        return await super().dispatch(request, call_next)


class Fast_API__Compute(Serverless__Fast_API):
    registry                  : Spec__Registry
    platform                  : Platform                                       # injected in tests; defaults to EC2__Platform in _mount_control_routes
    ui_root_override          : str = ''                                       # override spec ui root path for testing
    dashboard_root_override   : str = ''                                       # override dashboard static path for testing

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.registry.spec_ids():
            self.registry = Spec__Loader().load_all()

    def setup(self) -> 'Fast_API__Compute':
        self.setup_middlewares()                                                # boot-asserts key, registers auth + request-id middleware
        self._register_exception_handlers()
        self._mount_dashboard_ui()
        self._mount_spec_ui_static_files()
        self._mount_control_routes()
        self._mount_spec_routes()
        self._mount_legacy_routes()
        return self

    def setup_middlewares(self):
        self._assert_api_key_configured()
        super().setup_middlewares()

    def _assert_api_key_configured(self):                                      # fail-loud boot assertion; never fail-open
        key = os.environ.get(ENV_VAR__FAST_API__AUTH__API_KEY__VALUE, '')
        assert key,          (f'Fast_API__Compute refuses to start: '
                              f'{ENV_VAR__FAST_API__AUTH__API_KEY__VALUE} env var is unset')
        assert len(key) >= 16, (f'Fast_API__Compute refuses to start: '
                                f'API key is shorter than 16 characters')

    def setup_middleware__api_key_check(self,
                                        env_var__api_key_name  = ENV_VAR__FAST_API__AUTH__API_KEY__NAME ,
                                        env_var__api_key_value = ENV_VAR__FAST_API__AUTH__API_KEY__VALUE):
        if self.config.enable_api_key:
            self.app().add_middleware(_Middleware__Health_Bypass            ,
                                      env_var__api_key__name  = env_var__api_key_name  ,
                                      env_var__api_key__value = env_var__api_key_value ,
                                      allow_cors              = self.config.enable_cors)

    def _register_exception_handlers(self):
        app = self.app()

        @app.exception_handler(Exception__AWS__No_Credentials)
        async def no_credentials_handler(request: Request, exc: Exception__AWS__No_Credentials):
            return JSONResponse(status_code=503,
                                content={'detail': f'AWS credentials not configured: {exc}'})

    def _mount_dashboard_ui(self):                                             # /ui/ serves shared dashboard assets (api-client, node-state, shared components)
        from starlette.staticfiles import StaticFiles
        if self.dashboard_root_override:
            path = self.dashboard_root_override
        else:
            import sgraph_ai_service_playwright__api_site
            path = sgraph_ai_service_playwright__api_site.path
        self.app().mount('/ui', StaticFiles(directory=path, html=True), name='dashboard-ui')

    def _mount_legacy_routes(self):
        from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI import Fast_API__SP__CLI
        legacy_app = Fast_API__SP__CLI().setup().app()

        async def _with_deprecated_headers(scope, receive, send):              # ASGI wrapper — injects X-Deprecated on every legacy response
            async def _send(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    headers.append((b'x-deprecated'    , b'true'      ))
                    headers.append((b'x-migration-path', b'/api/specs'))
                    message = {**message, 'headers': headers}
                await send(message)
            await legacy_app(scope, receive, _send)

        self.app().mount('/legacy', _with_deprecated_headers)

    def _mount_spec_ui_static_files(self):
        from starlette.staticfiles                              import StaticFiles
        from sg_compute.core.spec.Spec__UI__Resolver           import Spec__UI__Resolver
        resolver = Spec__UI__Resolver(ui_root_override=self.ui_root_override)
        for spec_id in self.registry.spec_ids():
            ui_path = resolver.ui_path_for_spec(spec_id)
            if ui_path:
                self.app().mount(
                    f'/api/specs/{spec_id}/ui',
                    StaticFiles(directory=str(ui_path)),
                    name=f'spec-ui-{spec_id}',
                )

    def _mount_control_routes(self):
        platform    = self._live_platform()
        pod_manager = self._live_pod_manager()
        vault_writer = Vault__Spec__Writer(spec_registry=self.registry)
        ami_lister = self._live_ami_lister()
        self.add_routes(Routes__Compute__Health, prefix='/api/health', registry=self.registry)
        self.add_routes(Routes__Compute__Specs , prefix='/api/specs' , registry=self.registry)
        self.add_routes(Routes__Compute__Nodes , prefix='/api/nodes' , platform=platform      )
        self.add_routes(Routes__Compute__Pods  , prefix='/api/nodes' , manager=pod_manager    )
        self.add_routes(Routes__Compute__Stacks, prefix='/api/stacks')
        self.add_routes(Routes__Compute__AMIs  , prefix='/api/amis'  , lister=ami_lister      )
        self.add_routes(Routes__Vault__Spec    , prefix='/api/vault' , service=vault_writer   )

    @staticmethod
    def _live_ami_lister():
        from sg_compute.core.ami.service.AMI__Lister import AMI__Lister
        return AMI__Lister()

    @staticmethod
    def _live_pod_manager() -> Pod__Manager:
        from sg_compute.platforms.ec2.EC2__Platform import EC2__Platform
        return Pod__Manager(platform=EC2__Platform().setup())

    def _mount_spec_routes(self):
        loader = Spec__Routes__Loader(registry=self.registry)
        for spec_id, routes_cls in loader.load():
            service = self._make_service(spec_id, routes_cls)
            self.add_routes(routes_cls, prefix=f'/api/specs/{spec_id}', service=service)

    def _live_platform(self) -> Platform:
        if type(self.platform) is Platform:                                    # uninjected abstract base — use live EC2
            from sg_compute.platforms.ec2.EC2__Platform import EC2__Platform
            return EC2__Platform().setup()
        return self.platform

    @staticmethod
    def _make_service(spec_id: str, routes_cls):
        from osbot_utils.type_safe.Type_Safe import Type_Safe
        hints = getattr(routes_cls, '__annotations__', {})
        service_cls = hints.get('service')
        if service_cls is None or not (isinstance(service_cls, type) and issubclass(service_cls, Type_Safe)):
            return None
        svc = service_cls()
        if hasattr(svc, 'setup'):
            svc.setup()
        return svc
