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

from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.Spec__Routes__Loader                           import Spec__Routes__Loader
from sg_compute.control_plane.routes.Routes__Compute__Health                 import Routes__Compute__Health
from sg_compute.control_plane.routes.Routes__Compute__Nodes                  import Routes__Compute__Nodes
from sg_compute.control_plane.routes.Routes__Compute__Specs                  import Routes__Compute__Specs
from sg_compute.control_plane.routes.Routes__Compute__Stacks                 import Routes__Compute__Stacks
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader
from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry


class Fast_API__Compute(Fast_API):
    registry : Spec__Registry

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.registry.spec_ids():
            self.registry = Spec__Loader().load_all()

    def setup(self) -> 'Fast_API__Compute':
        self._mount_control_routes()
        self._mount_spec_routes()
        return self

    def _mount_control_routes(self):
        self.add_routes(Routes__Compute__Health, prefix='/api/health', registry=self.registry)
        self.add_routes(Routes__Compute__Specs , prefix='/api/specs' , registry=self.registry)
        self.add_routes(Routes__Compute__Nodes , prefix='/api/nodes' )
        self.add_routes(Routes__Compute__Stacks, prefix='/api/stacks')

    def _mount_spec_routes(self):
        loader = Spec__Routes__Loader(registry=self.registry)
        for spec_id, routes_cls in loader.load():
            service = self._make_service(spec_id, routes_cls)
            self.add_routes(routes_cls, prefix=f'/api/specs/{spec_id}', service=service)

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
