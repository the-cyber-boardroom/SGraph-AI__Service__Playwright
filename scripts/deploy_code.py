# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — deploy_code.py (v0.1.29 — one-command agentic deploy)
#
# Default mode (S3-only) — what the Day 4 CI calls:
#
#   1. Ensures the S3 bucket exists ({account}--sgraph-ai--{region}).
#   2. Packages sgraph_ai_service_playwright/ into a zip (via package_code).
#   3. Uploads to s3://<bucket>/apps/<app>/<stage>/v<X.Y.Z>.zip (immutable).
#
# Opt-in mode (--update-lambda) — used once the agentic-image Lambda exists:
#
#   4. Updates the Lambda's env vars:
#        • sets   AGENTIC_APP_NAME / AGENTIC_APP_STAGE / AGENTIC_APP_VERSION
#        • strips the v0.1.28-era SG_PLAYWRIGHT__CODE_* keys (one-shot cutover)
#   5. --smoke: probes the Function URL /admin/health and asserts
#      `code_source` now reads `s3:<bucket>/<key>…`.
#
# Why the split: at this stage no Docker image supports the AGENTIC_* loader
# shim, so flipping Lambda env vars would be a no-op. The CI uploads zips to
# S3 now so that once the agentic image ships, the zips are already staged
# and a single `--update-lambda` call activates them.
#
# Target round-trip: ~30 s cloud, ~5 s local (via AGENTIC_CODE_LOCAL_PATH).
#
# Called from:
#   • Day-2 onwards: CI Track B, local operators, deploy tests.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import json
import sys
import urllib.request

from osbot_aws.aws.lambda_.Lambda                                                                import Lambda
from osbot_aws.aws.s3.S3                                                                         import S3

from scripts.package_code                                                                        import (BUCKET_NAME_FORMAT ,
                                                                                                         DEFAULT_APP_NAME   ,
                                                                                                         KEY_FORMAT         ,
                                                                                                         build_code_zip     ,
                                                                                                         resolve_bucket_name,
                                                                                                         resolve_region     )
from sgraph_ai_service_playwright.consts.version                                                 import version__sgraph_ai_service_playwright


# Env vars to SET on the Lambda (new AGENTIC_* scheme)
AGENTIC_ENV_VARS_TO_SET = {'AGENTIC_APP_NAME'    ,
                           'AGENTIC_APP_STAGE'   ,
                           'AGENTIC_APP_VERSION' }

# Env vars to REMOVE from the Lambda (v0.1.28-era SG_PLAYWRIGHT__* loader vars)
# One-shot cutover — no dual-read compat per v0.1.29 plan §1.2.
LEGACY_ENV_VARS_TO_STRIP = {'SG_PLAYWRIGHT__LAMBDA_NAME'    ,
                            'SG_PLAYWRIGHT__CODE_S3_VERSION',
                            'SG_PLAYWRIGHT__CODE_LOCAL_PATH',
                            'SG_PLAYWRIGHT__IMAGE_VERSION'  ,
                            'SG_PLAYWRIGHT__CODE_SOURCE'    }

SMOKE_TEST_TIMEOUT_SEC = 10


def ensure_bucket(s3: S3, bucket_name: str, region_name: str) -> bool:              # Idempotent; safe to call on every deploy
    if s3.bucket_exists(bucket_name):
        return False
    s3.bucket_create(bucket_name, region=region_name)
    print(f'created bucket s3://{bucket_name}')
    return True


def upload_zip(bucket_name: str, s3_key: str, package_names: list = None) -> int:   # Returns byte count so callers / CI logs can sanity-check
    zb = build_code_zip(package_names)
    zb.save_to_s3(bucket_name, s3_key)
    size = len(zb.zip_bytes)
    print(f'uploaded {size:,} bytes to s3://{bucket_name}/{s3_key}')
    return size


def update_lambda_env(lambda_name: str, app_name: str, stage: str, version: str) -> dict:
    lambda_obj = Lambda(name=lambda_name)
    if not lambda_obj.exists():                                                     # Clean error > raw boto3 ResourceNotFoundException
        raise RuntimeError(f'lambda {lambda_name!r} does not exist. '
                           f'deploy_code.py only flips env vars on an existing function — '
                           f'the container image + Function URL must be provisioned once first '
                           f'(e.g. via Lambda__Docker__SGraph_AI__Service__Playwright.create_lambda() '
                           f'or tests/deploy/test_Deploy__Playwright__Service__to__{stage}.py).')

    info       = lambda_obj.info()
    current    = info.get('Configuration', {}).get('Environment', {}).get('Variables', {}) or {}

    merged = dict(current)
    for legacy in LEGACY_ENV_VARS_TO_STRIP:
        merged.pop(legacy, None)
    merged['AGENTIC_APP_NAME'   ] = app_name
    merged['AGENTIC_APP_STAGE'  ] = stage
    merged['AGENTIC_APP_VERSION'] = version

    lambda_obj.set_env_variables(merged).update_lambda_configuration()

    result = {'lambda_name': lambda_name,
              'set'        : {k: merged[k] for k in AGENTIC_ENV_VARS_TO_SET},
              'stripped'   : sorted(k for k in LEGACY_ENV_VARS_TO_STRIP if k in current)}
    print(f'lambda {lambda_name}: set {result["set"]}; stripped {result["stripped"]}')
    return result


def smoke_test(lambda_name: str) -> dict:                                           # Hits /admin/health — unauthenticated, returns {status, code_source}
    lambda_obj   = Lambda(name=lambda_name)
    function_url = lambda_obj.function_url()
    if not function_url:
        raise RuntimeError(f'lambda {lambda_name} has no Function URL configured')

    probe_url = function_url.rstrip('/') + '/admin/health'
    with urllib.request.urlopen(probe_url, timeout=SMOKE_TEST_TIMEOUT_SEC) as resp:
        body = json.loads(resp.read())

    code_source = body.get('code_source', '')
    print(f'smoke test {probe_url} -> code_source={code_source!r} status={body.get("status")!r}')
    if not code_source.startswith('s3:'):
        raise RuntimeError(f'expected code_source to start with "s3:", got {code_source!r}')
    return {'function_url': function_url, 'code_source': code_source, 'body': body}


def deploy(stage        : str                   ,
           app_name     : str = DEFAULT_APP_NAME ,
           lambda_name  : str = None             ,
           version      : str = None             ,
           region_name  : str = None             ,
           update_lambda: bool = False           ,
           smoke        : bool = False           ,
           package_names: list = None            ) -> dict:                         # Pass e.g. ['sgraph_ai_service_playwright__cli', 'scripts'] for sibling apps

    version      = version or str(version__sgraph_ai_service_playwright)
    lambda_name  = lambda_name or f'{app_name}-{stage}'
    s3           = S3()
    bucket_name  = resolve_bucket_name(region_name)
    s3_key       = KEY_FORMAT.format(app_name=app_name, stage=stage, version=version)

    ensure_bucket(s3, bucket_name, resolve_region(region_name))
    size = upload_zip(bucket_name, s3_key, package_names)

    result = {'bucket'       : bucket_name,
              'key'          : s3_key     ,
              'bytes'        : size       ,
              'app_name'     : app_name   ,
              'stage'        : stage      ,
              'version'      : version    ,
              'lambda_name'  : lambda_name,
              'package_names': package_names or ['sgraph_ai_service_playwright']}

    if update_lambda:                                                               # Opt-in: requires the Lambda to exist AND its image to understand AGENTIC_* env vars
        result['env_update'] = update_lambda_env(lambda_name, app_name, stage, version)
        if smoke:
            result['smoke'] = smoke_test(lambda_name)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Package the service, upload to S3, and (opt-in) flip the Lambda env to the new version.')
    parser.add_argument('--stage'         , required=True            , help="Deployment stage: 'dev', 'main', or 'prod'")
    parser.add_argument('--app-name'      , default=DEFAULT_APP_NAME , help=f'Logical app name (default: {DEFAULT_APP_NAME})')
    parser.add_argument('--lambda-name'   , default=None             , help='Lambda function name (default: {app-name}-{stage})')
    parser.add_argument('--version'       , default=None             , help='Override version (default: sgraph_ai_service_playwright/version file)')
    parser.add_argument('--region'        , default=None             , help='Override AWS region (default: boto3 session region)')
    parser.add_argument('--update-lambda' , action='store_true'      , help='Flip the Lambda env vars to point at the new version (requires the Lambda to exist AND run the agentic image)')
    parser.add_argument('--smoke'         , action='store_true'      , help='After --update-lambda, probe /admin/health to verify code_source. Ignored without --update-lambda.')
    parser.add_argument('--package'       , action='append', default=None, dest='package_names', metavar='NAME',
                                                                      help='Folder name(s) to include in the zip. Repeatable. Default: sgraph_ai_service_playwright')
    args = parser.parse_args()

    deploy(stage         = args.stage         ,
           app_name      = args.app_name      ,
           lambda_name   = args.lambda_name   ,
           version       = args.version       ,
           region_name   = args.region        ,
           update_lambda = args.update_lambda ,
           smoke         = args.smoke         ,
           package_names = args.package_names )
    return 0


if __name__ == '__main__':
    sys.exit(main())
