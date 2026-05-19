# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish admin — lambda_entry
# Canonical Lambda handler for the sg-compute-vault-publish-admin Lambda.
# Every request (HTML pages at /, /slug/<slug>/, /setup/; JSON under
# /api/v1/; the public /api/v1/status probe used by warming pages) is
# dispatched through the FastAPI app via Lambda_To_ASGI.
#
# Architecturally distinct from the waker Lambda:
#   - Waker  (lambdas/waker/lambda_entry.py) — plain-handler, slug routing,
#                                              warming-page state machine.
#   - Admin  (this file)                     — full FastAPI app, no slug
#                                              routing, all paths via ASGI.
#
# Both Lambdas live in the same package + share the service-level code
# (Vault_App__Service, Slug__Registry, Vault_App__Auto_DNS, schemas) — only
# the entry points differ.
# ═══════════════════════════════════════════════════════════════════════════════

import os

# FastAPI app cache — built once per warm container. Cold-start cost
# (~150ms for FastAPI init + route registration) is paid once.
_FAST_API_APP   = None
_LAMBDA_TO_ASGI = None


def _get_dispatcher():
    global _FAST_API_APP, _LAMBDA_TO_ASGI
    if _LAMBDA_TO_ASGI is None:
        from sg_compute_specs.vault_publish.lambdas.admin.Fast_API__Admin  import Fast_API__Admin
        from sg_compute_specs.vault_publish.lambdas.admin.Lambda_To_ASGI   import Lambda_To_ASGI
        _FAST_API_APP   = Fast_API__Admin().app()
        _LAMBDA_TO_ASGI = Lambda_To_ASGI(_FAST_API_APP)
    return _LAMBDA_TO_ASGI


def handler(event, context):
    # Lambda Function URL passes Function-URL v2.0 events; Lambda_To_ASGI
    # translates the event into an ASGI scope, runs the FastAPI app, and
    # returns a Function-URL v2.0 response dict.
    return _get_dispatcher()(event)


# Diagnostic env exposed at import-time (matches the waker's DEPLOY_INFO
# shape so `sg vp setup admin-lambda invoke` can hit a /health-style route
# and see what's actually deployed).
DEPLOY_INFO = {
    'service_version' : os.environ.get('ADMIN_SERVICE_VERSION', ''),
    'version'         : os.environ.get('ADMIN_VERSION', 'unknown'),
    'deployed_at'     : os.environ.get('ADMIN_DEPLOYED_AT',   ''),
    'deploy_id'       : os.environ.get('ADMIN_DEPLOY_ID',     ''),
    'deploy_region'   : os.environ.get('ADMIN_DEPLOY_REGION', ''),
    'deployed_by'     : os.environ.get('ADMIN_DEPLOYED_BY',   ''),
    'git_commit'      : os.environ.get('ADMIN_GIT_COMMIT',    ''),
}
