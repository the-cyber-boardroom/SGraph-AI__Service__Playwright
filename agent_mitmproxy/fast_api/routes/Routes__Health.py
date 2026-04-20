# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Routes__Health
#
# Two GET endpoints, pure delegation:
#   GET /health/info   -> Schema__Agent_Mitmproxy__Info  (name, version)
#   GET /health/status -> Schema__Health                  (liveness checks)
#
# /health/capabilities is deferred to Phase 2 where we add the interceptor
# upload + per-proxy-user surface.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                              import List

from osbot_fast_api.api.routes.Fast_API__Routes                                          import Fast_API__Routes
from osbot_utils.utils.Env                                                               import get_env

from agent_mitmproxy.consts                                                              import env_vars, paths
from agent_mitmproxy.consts.version                                                      import version__agent_mitmproxy
from agent_mitmproxy.schemas.service.Schema__Agent_Mitmproxy__Info                       import Schema__Agent_Mitmproxy__Info
from agent_mitmproxy.schemas.service.Schema__Health                                      import Schema__Health
from agent_mitmproxy.schemas.service.Schema__Health__Check                               import Schema__Health__Check


SERVICE_NAME         = 'agent-mitmproxy'
TAG__ROUTES_HEALTH   = 'health'
ROUTES_PATHS__HEALTH = [f'/{TAG__ROUTES_HEALTH}/info'   ,
                        f'/{TAG__ROUTES_HEALTH}/status' ]


def _ca_cert_path() -> str:
    return get_env(env_vars.ENV_VAR__CA_CERT_PATH) or paths.PATH__CA_CERT_PEM


def _interceptor_path() -> str:
    return get_env(env_vars.ENV_VAR__INTERCEPTOR_PATH) or paths.PATH__CURRENT_INTERCEPTOR


def _build_checks() -> List[Schema__Health__Check]:                                   # Probes the two files mitmweb needs to have produced for the service to be useful
    ca_path         = _ca_cert_path()
    interceptor     = _interceptor_path()
    ca_exists       = os.path.isfile(ca_path)
    script_exists   = os.path.isfile(interceptor)
    return [Schema__Health__Check(check_name = 'ca_cert_exists'          ,
                                  healthy    = ca_exists                 ,
                                  detail     = ca_path if ca_exists else f'missing: {ca_path}'),
            Schema__Health__Check(check_name = 'interceptor_script_exists',
                                  healthy    = script_exists             ,
                                  detail     = interceptor if script_exists else f'missing: {interceptor}')]


class Routes__Health(Fast_API__Routes):
    tag : str = TAG__ROUTES_HEALTH

    def info(self) -> Schema__Agent_Mitmproxy__Info:
        return Schema__Agent_Mitmproxy__Info(service_name    = SERVICE_NAME              ,
                                             service_version = version__agent_mitmproxy  )

    def status(self) -> Schema__Health:
        checks = _build_checks()
        return Schema__Health(healthy = all(c.healthy for c in checks) ,
                              checks  = checks                          )

    def setup_routes(self):
        self.add_route_get(self.info  )
        self.add_route_get(self.status)
