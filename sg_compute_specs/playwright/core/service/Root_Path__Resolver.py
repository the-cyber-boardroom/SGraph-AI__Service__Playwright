# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Root_Path__Resolver
#
# Single source of truth for the mount prefix the service believes it's served
# under. Used by:
#   • Fast_API__Playwright__Service.attach_root_path_middleware  → sets
#     scope['root_path'] so FastAPI emits prefixed /docs + /openapi.json URLs.
#   • Routes__Index.index → templates the same prefix into window.API_BASE so
#     the static UI's fetch() calls resolve correctly behind the proxy.
#
# Resolution precedence (highest first):
#   1. Per-request X-Forwarded-Prefix header — the reverse proxy already sends
#      it (see Fast_API__Reverse_Proxy.mount_one), so the same image works
#      behind any prefix without rebuild or env change.
#   2. SG_PLAYWRIGHT__ROOT_PATH env var (static override).
#   3. Default: /pw — the proxy-fronted vault-app deployment is the predominant
#      use case; standalone deployments can disable via env=/ (see below).
#
# Escape hatch — true standalone at root:
#   SG_PLAYWRIGHT__ROOT_PATH=/   → resolves to '' (no prefix). The single '/'
#   sentinel is the explicit "I am served at root" signal; we cannot tell
#   "env unset" from "env empty" with os.environ, so empty falls through to
#   the default.
#
# All return values are normalised: no trailing slash; '' means no prefix.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                            import Optional

from osbot_utils.type_safe.Type_Safe                   import Type_Safe
from osbot_utils.utils.Env                             import get_env

from sg_compute_specs.playwright.core.consts.env_vars  import ENV_VAR__ROOT_PATH


DEFAULT_ROOT_PATH       = '/pw'                                                         # vault-app reverse-proxy default
HEADER__FORWARDED_PREFIX = 'x-forwarded-prefix'
SENTINEL__NO_PREFIX     = '/'                                                           # env=/ → explicit standalone (no prefix)


class Root_Path__Resolver(Type_Safe):

    def resolve(self, request=None) -> str:                                             # request: optional starlette/fastapi Request; when supplied, header wins
        if request is not None:
            header_value = request.headers.get(HEADER__FORWARDED_PREFIX)
            if header_value:
                return header_value.rstrip('/')
        env_value = (get_env(ENV_VAR__ROOT_PATH) or '').strip()
        if env_value == SENTINEL__NO_PREFIX:                                            # explicit "I am at root"
            return ''
        if env_value:
            return env_value.rstrip('/')
        return DEFAULT_ROOT_PATH
