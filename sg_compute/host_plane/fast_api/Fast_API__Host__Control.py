# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Fast_API__Host__Control
# FastAPI service running on every EC2 instance as the privileged control plane.
# Port 9000 on the host (mapped from container port 8000).
# API-key auth is always ON: key is generated at EC2 boot and pushed to vault.
#
# CORS: CORSMiddleware is added as the outermost layer (after super().setup_middlewares)
# so it intercepts OPTIONS preflights before the API-key middleware sees them.
# setup_middleware__cors() is suppressed (no-op) to avoid a duplicate middleware
# and to swap in allow_methods=["*"], allow_headers=["*"], allow_credentials=False.
#
# /docs-auth exclusion: setup_middleware__api_key_check() is overridden to use a
# local subclass that excludes /docs-auth from auth (serves static HTML only).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                   import Serverless__Fast_API
from osbot_fast_api.api.schemas.consts.consts__Fast_API                        import (ENV_VAR__FAST_API__AUTH__API_KEY__NAME ,
                                                                                        ENV_VAR__FAST_API__AUTH__API_KEY__VALUE)

from sg_compute.host_plane.fast_api.exception_handlers                         import register_type_safe_handlers
from sg_compute.host_plane.fast_api.routes.Routes__Host__Docs                  import Routes__Host__Docs
from sg_compute.host_plane.fast_api.routes.Routes__Host__Logs                  import Routes__Host__Logs
from sg_compute.host_plane.fast_api.routes.Routes__Host__Pods                  import Routes__Host__Pods
from sg_compute.host_plane.fast_api.routes.Routes__Host__Shell                 import Routes__Host__Shell
from sg_compute.host_plane.fast_api.routes.Routes__Host__Status                import Routes__Host__Status


class Fast_API__Host__Control(Serverless__Fast_API):

    def setup(self):
        result = super().setup()
        register_type_safe_handlers(self.app())
        return result

    def setup_middleware__cors(self):                                           # Suppressed — CORSMiddleware added as outermost in setup_middlewares()
        pass

    def setup_middleware__api_key_check(self,
                                        env_var__api_key_name  = ENV_VAR__FAST_API__AUTH__API_KEY__NAME ,
                                        env_var__api_key_value = ENV_VAR__FAST_API__AUTH__API_KEY__VALUE):
        from osbot_fast_api.api.middlewares.Middleware__Check_API_Key import Middleware__Check_API_Key

        class _Middleware(Middleware__Check_API_Key):                          # Excludes /docs-auth from auth (serves static HTML only)
            async def dispatch(self, request, call_next):
                if request.url.path == '/docs-auth':
                    return await call_next(request)
                return await super().dispatch(request, call_next)

        if self.config.enable_api_key:
            self.app().add_middleware(_Middleware                                                   ,
                                      env_var__api_key__name  = env_var__api_key_name              ,
                                      env_var__api_key__value = env_var__api_key_value             ,
                                      allow_cors              = False                              ) # CORSMiddleware (outermost) handles OPTIONS; no need for the shortcut here

    def setup_middlewares(self):
        super().setup_middlewares()                                             # adds: detect_disconnect, (cors=noop), _Middleware, request_id
        from starlette.middleware.cors import CORSMiddleware
        self.app().add_middleware(CORSMiddleware,                               # Outermost: handles OPTIONS preflights before api_key_check
                                  allow_origins     = ["*"]  ,
                                  allow_methods     = ["*"]  ,
                                  allow_headers     = ["*"]  ,
                                  allow_credentials = False  )

    def setup_routes(self):
        self.add_routes(Routes__Host__Docs  )
        self.add_routes(Routes__Host__Logs  )
        self.add_routes(Routes__Host__Pods  )
        self.add_routes(Routes__Host__Shell )
        self.add_routes(Routes__Host__Status)
