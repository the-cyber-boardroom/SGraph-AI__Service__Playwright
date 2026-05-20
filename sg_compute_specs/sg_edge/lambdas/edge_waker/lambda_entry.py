# ═══════════════════════════════════════════════════════════════════════════════
# sg_edge edge-waker — lambda_entry
# Canonical handler for the sg-edge-waker Lambda. Standard osbot serverless shape:
#   1. Inside Lambda (AWS_REGION set): load the combined dependency zip from S3
#      onto sys.path BEFORE importing the app (platform-correct wheels).
#   2. Build the Serverless__Fast_API app; capture handler() (Mangum) + app().
#   3. run(event, context) is the AWS entry point.
# Local (no AWS_REGION): the dep load no-ops; imports resolve from the venv.
# A broken cold start inside Lambda is captured into `error` and returned as a
# readable string; locally it re-raises. Mirrors vault_publish/lambdas/waker.
# ═══════════════════════════════════════════════════════════════════════════════

import os

if os.getenv('AWS_REGION'):                                                          # only inside Lambda
    from sg_compute._for_osbot_aws.Lambda__Dependencies__Loader            import load_combined_dependency
    from sg_compute_specs.sg_edge.lambdas.edge_waker.edge_waker__config    import (
        EDGE_WAKER__DEPS_BASE_NAME, EDGE_WAKER__LAMBDA_DEPENDENCIES)
    load_combined_dependency(EDGE_WAKER__DEPS_BASE_NAME, EDGE_WAKER__LAMBDA_DEPENDENCIES)

error = None; handler = None; app = None
try:
    from sg_compute_specs.sg_edge.lambdas.edge_waker.Fast_API__Edge_Waker import Fast_API__Edge_Waker
    with Fast_API__Edge_Waker() as _:
        _.setup()
        handler = _.handler()
        app     = _.app()
except Exception as exc:
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is None:                                # re-raise locally
        raise
    error = f'CRITICAL ERROR: Failed to start edge-waker service with:\n\n{type(exc).__name__}: {exc}'


def run(event, context=None):                                                        # AWS Lambda entry point
    if error:
        return error
    return handler(event, context)
