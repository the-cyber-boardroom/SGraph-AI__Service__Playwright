# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Fast_API__Host__Control
# FastAPI service running on every EC2 instance as the privileged control plane.
# Port 9000 on the host (mapped from container port 8000).
# API-key auth is always ON: key is generated at EC2 boot and pushed to vault.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                                   import Serverless__Fast_API

from sgraph_ai_service_playwright__host.fast_api.exception_handlers                            import register_type_safe_handlers
from sgraph_ai_service_playwright__host.fast_api.routes.Routes__Host__Containers               import Routes__Host__Containers
from sgraph_ai_service_playwright__host.fast_api.routes.Routes__Host__Shell                    import Routes__Host__Shell
from sgraph_ai_service_playwright__host.fast_api.routes.Routes__Host__Status                   import Routes__Host__Status


class Fast_API__Host__Control(Serverless__Fast_API):

    def setup(self):
        result = super().setup()
        register_type_safe_handlers(self.app())
        return result

    def setup_routes(self):
        self.add_routes(Routes__Host__Containers)
        self.add_routes(Routes__Host__Shell     )
        self.add_routes(Routes__Host__Status    )
