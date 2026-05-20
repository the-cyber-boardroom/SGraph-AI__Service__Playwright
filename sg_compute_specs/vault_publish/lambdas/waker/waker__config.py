# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish waker — waker__config
# Single source of truth for the waker Lambda's pinned dependency list, names,
# IFD version, and deploy metadata. The dependency list is consumed in two
# places — the cold-start Loader (lambda_entry) and the build-time Builder
# (Setup__Lambda) — and MUST be byte-identical in both (the S3 deps object name
# is a hash of it).
# ═══════════════════════════════════════════════════════════════════════════════

import os

WAKER__LAMBDA_NAME      = 'sg-compute-vault-publish-waker'
WAKER__DEPS_BASE_NAME   = 'sg-compute-vault-publish-waker'                            # S3 deps-zip prefix
WAKER__FAST_API__TITLE  = 'SG/Vault Waker'
WAKER__FAST_API__DESC   = ('vault-publish edge router — resolves <slug>.<zone> to its EC2 vault, '
                           'wakes a stopped instance, and proxies once healthy')

# Pinned dependency list (every version explicit — the hash that names the S3
# deps object is derived from this exact list). osbot-fast-api-serverless pulls
# fastapi + starlette + mangum + osbot-fast-api + osbot-utils transitively.
WAKER__LAMBDA_DEPENDENCIES = ['osbot-fast-api-serverless==v1.34.0']

# ── IFD version (per-lambda, manually bumped) + env-overridable deploy meta ───
_VERSION_FILE = os.path.join(os.path.dirname(__file__), 'version')
_FILE_VERSION = open(_VERSION_FILE).read().strip() if os.path.isfile(_VERSION_FILE) else 'unknown'
WAKER_VERSION = os.environ.get('WAKER_VERSION', _FILE_VERSION)

DEPLOY_INFO = {
    'service_version': os.environ.get('WAKER_SERVICE_VERSION', ''),
    'version'        : WAKER_VERSION,
    'deployed_at'    : os.environ.get('WAKER_DEPLOYED_AT',   ''),
    'deploy_id'      : os.environ.get('WAKER_DEPLOY_ID',     ''),
    'deploy_region'  : os.environ.get('WAKER_DEPLOY_REGION', ''),
    'deployed_by'    : os.environ.get('WAKER_DEPLOYED_BY',   ''),
    'git_commit'     : os.environ.get('WAKER_GIT_COMMIT',    ''),
}


def waker_zone() -> str:
    return os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
