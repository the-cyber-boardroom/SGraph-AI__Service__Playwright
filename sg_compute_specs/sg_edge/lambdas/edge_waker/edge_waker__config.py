# ═══════════════════════════════════════════════════════════════════════════════
# sg_edge edge-waker — edge_waker__config
# Single source of truth for the Edge Waker Lambda's pinned dependency list,
# names, version, and per-edge knobs. The dependency list is consumed in two
# places — the cold-start Loader (lambda_entry) and the build-time Builder
# (Setup__Lambda, Slice 5) — and MUST be byte-identical in both (the S3 deps
# object name is a hash of it). Mirrors vault_publish/lambdas/waker/waker__config.
# ═══════════════════════════════════════════════════════════════════════════════

import os

EDGE_WAKER__LAMBDA_NAME     = 'sg-edge-waker'
EDGE_WAKER__DEPS_BASE_NAME  = 'sg-edge-waker'                                         # S3 deps-zip prefix
EDGE_WAKER__FAST_API__TITLE = 'SG/Edge Waker'
EDGE_WAKER__FAST_API__DESC  = ('SG/Edge control plane — convergent reconciliation of the '
                               'OpenResty proxy fleet (cold-cold boot, scale check, idle teardown)')

# Pinned dependency list — every version explicit (the S3 deps-object name is a
# hash of this list). osbot-fast-api-serverless pulls fastapi + starlette +
# mangum + osbot-fast-api + osbot-utils transitively.
EDGE_WAKER__LAMBDA_DEPENDENCIES = ['osbot-fast-api-serverless==v1.34.0']

# ── per-edge knobs (env-overridable; brief 02 defaults) ───────────────────────
def edge_parent() -> str:                                                            # the parent domain this Edge Waker governs
    return os.environ.get('SG_EDGE__PARENT_DOMAIN', os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', ''))

def edge_proxy_target_count() -> int:                                                # static fleet size while vaults are active (Phase 3 makes this dynamic)
    return int(os.environ.get('SG_EDGE__PROXY_TARGET_COUNT', '2'))

def edge_idle_teardown_threshold() -> int:                                           # consecutive zero-vault idle-checks before teardown
    return int(os.environ.get('SG_EDGE__IDLE_TEARDOWN_THRESHOLD', '3'))

# ── version (per-lambda, manually bumped) ─────────────────────────────────────
_VERSION_FILE       = os.path.join(os.path.dirname(__file__), 'version')
_FILE_VERSION       = open(_VERSION_FILE).read().strip() if os.path.isfile(_VERSION_FILE) else 'unknown'
EDGE_WAKER_VERSION  = os.environ.get('SG_EDGE__WAKER_VERSION', _FILE_VERSION)
