# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__Compute
# Control-plane FastAPI for the SG/Compute service.
#
# Mounted routes
# ──────────────
#   /api/health             Routes__Compute__Health   (ping + readiness)
#   /api/specs              Routes__Compute__Specs    (catalogue + per-spec info)
#   /api/nodes              Routes__Compute__Nodes    (cross-spec node list)
#   /api/stacks             Routes__Compute__Stacks   (cross-spec stack list)
#   /api/specs/{spec_id}/*  per-spec Routes__*__Stack (discovered by convention)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                  import Request
from fastapi.responses                                                        import JSONResponse
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.Spec__Routes__Loader                           import Spec__Routes__Loader
from sg_compute.control_plane.routes.Routes__Compute__Health                 import Routes__Compute__Health
from sg_compute.control_plane.routes.Routes__Compute__Nodes                  import Routes__Compute__Nodes
from sg_compute.control_plane.routes.Routes__Compute__Specs                  import Routes__Compute__Specs
from sg_compute.control_plane.routes.Routes__Compute__Stacks                 import Routes__Compute__Stacks
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.platforms.exceptions.Exception__AWS__No_Credentials          import Exception__AWS__No_Credentials


class Fast_API__Compute(Fast_API):
    registry : Spec__Registry
    platform : Platform                                                        # injected in tests; defaults to EC2__Platform in _mount_control_routes

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.registry.spec_ids():
            self.registry = Spec__Loader().load_all()

    def setup(self) -> 'Fast_API__Compute':
        self._register_exception_handlers()
        self._mount_control_routes()
        self._mount_spec_routes()
        return self

    def _register_exception_handlers(self):
        app = self.app()

        @app.exception_handler(Exception__AWS__No_Credentials)
        async def no_credentials_handler(request: Request, exc: Exception__AWS__No_Credentials):
            return JSONResponse(status_code=503,
                                content={'detail': f'AWS credentials not configured: {exc}'})

    def _mount_control_routes(self):
        platform = self._live_platform()
        self.add_routes(Routes__Compute__Health, prefix='/api/health', registry=self.registry)
        self.add_routes(Routes__Compute__Specs , prefix='/api/specs' , registry=self.registry)
        self.add_routes(Routes__Compute__Nodes , prefix='/api/nodes' , platform=platform      )
        self.add_routes(Routes__Compute__Stacks, prefix='/api/stacks')

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
