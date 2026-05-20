# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish admin — admin__config
# Single source of truth for the admin Lambda's pinned dependency list +
# constants. The dependency list is consumed in two places — the cold-start
# Loader (lambda_entry) and the build-time Builder (Setup__Admin__Lambda) —
# and MUST be byte-identical in both (the S3 object name is a hash of it).
# ═══════════════════════════════════════════════════════════════════════════════

import os

ADMIN__LAMBDA_NAME          = 'sg-compute-vault-publish-admin'
ADMIN__DEPS_BASE_NAME       = 'sg-compute-vault-publish-admin'                        # S3 deps-zip prefix
ADMIN__FAST_API__TITLE      = 'SG/Vault Admin'
ADMIN__FAST_API__DESC       = 'vault-publish control plane — inventory, per-slug status, register/unpublish'

# Pinned dependency list (every version explicit — the hash that names the S3
# deps object is derived from this exact list). osbot-fast-api-serverless pulls
# fastapi + starlette + mangum + osbot-fast-api + osbot-utils transitively;
# python-multipart is needed for the login Form.
ADMIN__LAMBDA_DEPENDENCIES  = ['osbot-fast-api-serverless==v1.34.0',
                               'python-multipart==0.0.29'          ]

# Admin API-key auth (set by Setup__Admin__Lambda at deploy time)
ENV_VAR__ADMIN__API_KEY_NAME  = 'SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME'
ENV_VAR__ADMIN__API_KEY_VALUE = 'SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE'


def admin_zone() -> str:
    return os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
