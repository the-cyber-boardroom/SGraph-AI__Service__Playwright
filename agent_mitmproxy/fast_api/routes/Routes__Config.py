# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Routes__Config
#
#   GET /config/interceptor — returns the current interceptor script source
#                             + path + size. Phase 2 adds PUT with persistence.
#
# The path is taken from env AGENT_MITMPROXY__INTERCEPTOR_PATH, defaulting to
# /app/current_interceptor.py (seeded by entrypoint.sh from the baked default).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                                                                             import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                                          import Fast_API__Routes
from osbot_utils.utils.Env                                                               import get_env

from agent_mitmproxy.consts                                                              import env_vars, paths
from agent_mitmproxy.schemas.config.Schema__Interceptor__Source                          import Schema__Interceptor__Source


TAG__ROUTES_CONFIG   = 'config'
ROUTES_PATHS__CONFIG = [f'/{TAG__ROUTES_CONFIG}/interceptor']


def _resolve_interceptor_path() -> str:
    return get_env(env_vars.ENV_VAR__INTERCEPTOR_PATH) or paths.PATH__CURRENT_INTERCEPTOR


class Routes__Config(Fast_API__Routes):
    tag : str = TAG__ROUTES_CONFIG

    def interceptor(self) -> Schema__Interceptor__Source:
        script_path = _resolve_interceptor_path()
        if not os.path.isfile(script_path):
            raise HTTPException(status_code=503, detail=f'Interceptor script not found at {script_path} — entrypoint.sh seeds it on container start')
        with open(script_path, 'r') as f:
            source = f.read()
        return Schema__Interceptor__Source(path       = script_path    ,
                                           size_bytes = len(source)    ,
                                           source     = source         )

    def setup_routes(self):
        self.add_route_get(self.interceptor)
