# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish waker — lambda_entry
# Canonical handler for the sg-compute-vault-publish-waker Lambda.
#
# Cold-start sequence (the standard osbot serverless shape):
#   1. If inside Lambda (AWS_REGION set): load the combined dependency zip from
#      S3 onto sys.path BEFORE importing the app (so fastapi/pydantic/etc.
#      resolve against the platform-correct wheels, not the build host's).
#   2. Build the Serverless__Fast_API app, capture handler() (Mangum) + app().
#   3. run(event, context) is the AWS entry point.
#
# Local (no AWS_REGION): the dep load no-ops and imports resolve from the venv.
# A broken cold start inside Lambda is captured into `error` and returned as a
# readable string instead of an opaque 502; locally it re-raises.
# ═══════════════════════════════════════════════════════════════════════════════

import os

if os.getenv('AWS_REGION'):                                                          # only inside Lambda
    from sg_compute._for_osbot_aws.Lambda__Dependencies__Loader     import load_combined_dependency
    from sg_compute_specs.vault_publish.lambdas.waker.waker__config import (
        WAKER__DEPS_BASE_NAME, WAKER__LAMBDA_DEPENDENCIES)
    load_combined_dependency(WAKER__DEPS_BASE_NAME, WAKER__LAMBDA_DEPENDENCIES)

error = None; handler = None; app = None
try:
    from sg_compute_specs.vault_publish.lambdas.waker.Fast_API__Waker import Fast_API__Waker
    with Fast_API__Waker() as _:
        _.setup()
        handler = _.handler()
        app     = _.app()
except Exception as exc:
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is None:                                # re-raise locally
        raise
    error = f'CRITICAL ERROR: Failed to start waker service with:\n\n{type(exc).__name__}: {exc}'


def run(event, context=None):                                                        # AWS Lambda entry point
    if error:
        return error
    return handler(event, context)
