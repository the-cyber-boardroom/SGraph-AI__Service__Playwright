# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__Compute
# Control-plane FastAPI for the SG/Compute service.
#
# Mounted routes
# ──────────────
#   /api/health                   Routes__Compute__Health   (ping + readiness)
#   /api/specs                    Routes__Compute__Specs    (catalogue + per-spec info)
#   /api/nodes                    Routes__Compute__Nodes    (cross-spec node list)
#   /api/stacks                   Routes__Compute__Stacks   (cross-spec stack list)
#   /api/vault                    Routes__Vault__Spec       (per-spec vault write/list/delete)
#   /api/specs/{spec_id}/ui/*     StaticFiles               (spec UI assets — mounted when ui/ exists)
#   /api/specs/{spec_id}/*        per-spec Routes__*__Stack (discovered by convention)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                  import Request
from fastapi.responses                                                        import JSONResponse
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.Spec__Routes__Loader                           import Spec__Routes__Loader
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


class Fast_API__Compute(Fast_API):
    registry         : Spec__Registry
    platform         : Platform                                                # injected in tests; defaults to EC2__Platform in _mount_control_routes
    ui_root_override : str = ''                                                # override ui root path for testing

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.registry.spec_ids():
            self.registry = Spec__Loader().load_all()

    def setup(self) -> 'Fast_API__Compute':
        self._register_exception_handlers()
        self._mount_spec_ui_static_files()
        self._mount_control_routes()
        self._mount_spec_routes()
        self._mount_legacy_routes()
        return self

    def _register_exception_handlers(self):
        app = self.app()

        @app.exception_handler(Exception__AWS__No_Credentials)
        async def no_credentials_handler(request: Request, exc: Exception__AWS__No_Credentials):
            return JSONResponse(status_code=503,
                                content={'detail': f'AWS credentials not configured: {exc}'})

    def _mount_legacy_routes(self):
        from sgraph_ai_service_playwright__cli.catalog.fast_api.routes.Routes__Stack__Catalog import Routes__Stack__Catalog
        from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service        import Stack__Catalog__Service
        from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                   import Plugin__Registry, PLUGIN_FOLDERS
        from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                       import Ec2__Service
        from sgraph_ai_service_playwright__cli.observability.service.Observability__Service   import Observability__Service
        from sg_compute.control_plane.legacy_routes.Routes__Ec2__Playwright                   import Routes__Ec2__Playwright
        from sg_compute.control_plane.legacy_routes.Routes__Observability                     import Routes__Observability

        plugin_registry = Plugin__Registry()
        plugin_registry.plugin_folders = list(PLUGIN_FOLDERS)
        plugin_registry.discover().setup_all()

        catalog_service = Stack__Catalog__Service(plugin_registry=plugin_registry)
        ec2_service     = Ec2__Service()
        obs_service     = Observability__Service()

        self.add_routes(Routes__Stack__Catalog , prefix='/legacy/catalog'        , service=catalog_service)
        self.add_routes(Routes__Ec2__Playwright , prefix='/legacy/ec2/playwright'  , service=ec2_service   )
        self.add_routes(Routes__Observability   , prefix='/legacy/observability'   , service=obs_service   )
        for routes_cls, svc in plugin_registry.route_service_pairs():
            tag = str(routes_cls().tag)                                            # tag is the URL prefix in the legacy SP CLI
            self.add_routes(routes_cls, prefix=f'/legacy/{tag}', service=svc)

        self._add_deprecated_header_middleware()

    def _add_deprecated_header_middleware(self):
        app = self.app()

        @app.middleware('http')
        async def _legacy_deprecation(request, call_next):
            response = await call_next(request)
            if request.url.path.startswith('/legacy'):
                response.headers['X-Deprecated']    = 'true'
                response.headers['X-Migration-Path'] = '/api/specs'
            return response

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
        self.add_routes(Routes__Compute__Health, prefix='/api/health', registry=self.registry)
        self.add_routes(Routes__Compute__Specs , prefix='/api/specs' , registry=self.registry)
        self.add_routes(Routes__Compute__Nodes , prefix='/api/nodes' , platform=platform      )
        self.add_routes(Routes__Compute__Pods  , prefix='/api/nodes' , manager=pod_manager   )
        self.add_routes(Routes__Compute__Stacks, prefix='/api/stacks')
        self.add_routes(Routes__Vault__Spec    , prefix='/api/vault' , service=vault_writer  )

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
