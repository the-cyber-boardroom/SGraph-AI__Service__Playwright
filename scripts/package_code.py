# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — package_code.py (v0.1.28 — S3-zip hot-swap)
#
# Packages the current `sgraph_ai_service_playwright/` Python source into a zip
# and uploads it to the dev/prod account S3 bucket under:
#
#   s3://<account-id>--sg-playwright--<region>/<lambda-name>/code/<version>.zip
#
# Every upload is IMMUTABLE — the version string comes from the repo-root
# `sgraph_ai_service_playwright/version` file, and we never overwrite.
# There is NO `latest.zip` / `last-known-good.zip`. The Lambda's
# `SG_PLAYWRIGHT__CODE_S3_VERSION` env var IS the pointer; rollback = flip the
# env var back to an older version.
#
# Called from:
#   • CI Track B — after a version bump lands on `dev`
#   • Deploy tests — test_Deploy_Code__to__dev.test_1__upload_new_code_zip
#   • Local operators — during initial migration or manual rollback prep
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import os
import sys

import boto3

from osbot_aws.aws.s3.S3                                                                        import S3
from osbot_aws.aws.s3.S3__Zip_Bytes                                                             import S3__Zip_Bytes

from sgraph_ai_service_playwright.consts.version                                                import version__sgraph_ai_service_playwright


PACKAGE_NAME       = 'sgraph_ai_service_playwright'                                 # Must match the folder name at repo root
SOURCE_FILE_REGEX  = r'.*\.py$'                                                     # Only Python sources; no __pycache__ or compiled files
BUCKET_NAME_FORMAT = '{account_id}--sg-playwright--{region_name}'                   # Matches the boot-shim's expectation in lambda_entry.py:72


def resolve_bucket_name(region_name: str = None) -> str:                            # Lazy sts call — avoids loading AWS creds during simple `--help` invocations
    sts         = boto3.client('sts')
    account_id  = sts.get_caller_identity()['Account']
    region_name = region_name or boto3.session.Session().region_name
    return BUCKET_NAME_FORMAT.format(account_id=account_id, region_name=region_name)


def build_code_zip() -> S3__Zip_Bytes:                                              # Pure packaging — no S3 yet, so callers can inspect the bytes
    zb = S3__Zip_Bytes(s3=S3())
    zb.add_folder__from_disk(PACKAGE_NAME, SOURCE_FILE_REGEX)
    return zb


def deploy_code(lambda_name: str, version: str = None, region_name: str = None) -> dict:
    version      = version or str(version__sgraph_ai_service_playwright)
    bucket_name  = resolve_bucket_name(region_name)
    s3_key       = f'{lambda_name}/code/{version}.zip'

    zb           = build_code_zip()
    zb.save_to_s3(bucket_name, s3_key)

    result = {'bucket'   : bucket_name         ,
              'key'      : s3_key              ,
              'version'  : version             ,
              'bytes'    : len(zb.zip_bytes)    }                                   # Size surfaced in CI logs — quick sanity check for accidental empty zips
    print(f'uploaded {result["bytes"]:,} bytes to s3://{bucket_name}/{s3_key}')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Package and upload the sg-playwright code zip.')
    parser.add_argument('--lambda-name', required=True, help='Lambda function name, e.g. sg-playwright-dev')
    parser.add_argument('--version'    , default=None , help='Override version string (default: repo version file)')
    parser.add_argument('--region'     , default=None , help='Override AWS region (default: boto3 session region)')
    args = parser.parse_args()

    deploy_code(lambda_name=args.lambda_name, version=args.version, region_name=args.region)
    return 0


if __name__ == '__main__':
    sys.exit(main())
