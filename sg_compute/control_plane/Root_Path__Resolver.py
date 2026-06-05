# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Root_Path__Resolver (control plane)
#
# Single source of truth for the URL prefix this service believes it's served
# under. Used by Fast_API__Compute.attach_root_path_middleware to set
# scope['root_path'] so FastAPI emits prefixed /docs + /openapi.json URLs.
#
# Resolution precedence (highest first):
#   1. Per-request X-Forwarded-Prefix header — the vault Fast_API__Reverse_Proxy
#      already sends it on every proxied request, so the same image works
#      behind any prefix without rebuild or env change.
#   2. SG_COMPUTE__ROOT_PATH env var (static override).
#   3. Default: '' (no prefix). This is the "no positive signal" case —
#      direct callers and TestClients see normal behaviour. Behind the
#      vault proxy, the X-Forwarded-Prefix header (always sent) supplies
#      the '/host' prefix dynamically; behind another proxy the operator
#      sets the env var. We don't bake '/host' into the default the way
#      sg-playwright bakes '/pw' because the control plane mounts static
#      files at root and a non-empty default shifts the URL space those
#      mounts assume, breaking direct-access tests.
#
# Escape hatch — true standalone at root override:
#   SG_COMPUTE__ROOT_PATH=/   → resolves to '' (explicit; same as unset).
#
# All return values are normalised: no trailing slash; '' means no prefix.
#
# NOTE: this is the same pattern as sg_compute_specs/playwright's
# Root_Path__Resolver. Both deserve to live in one shared module (probably
# sg_compute/fast_api/, en route to OSBot__Fast_API upstream) — see the
# Page__Factory refactor for the prior art on collapsing this kind of
# drift-prone duplication. Tracked as a fast-follow consolidation.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe   import Type_Safe
from osbot_utils.utils.Env             import get_env


ENV_VAR__ROOT_PATH       = 'SG_COMPUTE__ROOT_PATH'
DEFAULT_ROOT_PATH        = ''                                                        # no positive signal → no prefix. Proxy supplies '/host' via X-Forwarded-Prefix.
HEADER__FORWARDED_PREFIX = 'x-forwarded-prefix'
SENTINEL__NO_PREFIX      = '/'                                                       # env=/ → explicit standalone (no prefix); same effect as unset
PROXY_PREFIX             = '/host'                                                   # The convention used by Fast_API__Reverse_Proxy when mounting `host=http://...` — for reference / CLI use, NOT auto-applied here.


class Root_Path__Resolver(Type_Safe):

    def resolve(self, request=None) -> str:                                          # request: optional starlette/fastapi Request; when supplied, header wins
        if request is not None:
            header_value = request.headers.get(HEADER__FORWARDED_PREFIX)
            if header_value:
                return header_value.rstrip('/')
        env_value = (get_env(ENV_VAR__ROOT_PATH) or '').strip()
        if env_value == SENTINEL__NO_PREFIX:                                         # explicit "I am at root"
            return ''
        if env_value:
            return env_value.rstrip('/')
        return DEFAULT_ROOT_PATH
