# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — package_code.py (v0.1.29 — agentic S3-zip hot-swap)
#
# Packages the current `sgraph_ai_service_playwright/` Python source into a zip
# and uploads it to the account S3 bucket under:
#
#   s3://<account-id>--sgraph-ai--<region>/apps/<app-name>/<stage>/<version>.zip
#
# Every upload is IMMUTABLE — the version string comes from the repo-root
# `sgraph_ai_service_playwright/version` file, and we never overwrite.
# There is NO `latest.zip` / `last-known-good.zip`. The Lambda's
# AGENTIC_APP_VERSION env var IS the pointer; rollback = flip the env var
# back to an older version.
#
# Called from:
#   • scripts/deploy_code.py — the end-to-end one-command deploy (Day 2)
#   • Deploy tests — test_Deploy_Code__to__dev.test_1__upload_new_code_zip
#   • Local operators — during initial migration or manual rollback prep
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

from osbot_aws.AWS_Config                                                                       import AWS_Config
from osbot_aws.aws.s3.S3                                                                        import S3
from osbot_aws.aws.s3.S3__Zip_Bytes                                                             import S3__Zip_Bytes
from osbot_utils.utils.Files                                                                    import files_list
from osbot_utils.utils.Regex                                                                    import list__match_regexes

from sgraph_ai_service_playwright.consts.version                                                import version__sgraph_ai_service_playwright


PACKAGE_NAME       = 'sgraph_ai_service_playwright'                                 # Must match the folder name at repo root
SOURCE_FILE_REGEX  = r'.*\.(py|html|js|css)$'                                       # Python sources + static UI assets (html/js/css for api_site); no __pycache__ or compiled files
BUCKET_NAME_FORMAT = '{account_id}--sgraph-ai--{region_name}'                       # Matches the boot-shim's expectation in lambda_entry.py
KEY_FORMAT         = 'apps/{app_name}/{stage}/{version}.zip'                        # Matches the boot-shim's expectation in lambda_entry.py
DEFAULT_APP_NAME   = 'sg-playwright'


def resolve_region(region_name: str = None) -> str:                                # Explicit > AWS_Config (reads env / boto3 session); callers share one resolved value
    return region_name or AWS_Config().region_name()


def resolve_bucket_name(region_name: str = None) -> str:                            # AWS_Config handles sts caller-identity + region resolution
    aws_config  = AWS_Config()
    account_id  = aws_config.account_id()
    region_name = region_name or aws_config.region_name()
    return BUCKET_NAME_FORMAT.format(account_id=account_id, region_name=region_name)


def build_code_zip(package_names: list = None) -> S3__Zip_Bytes:                    # Pure packaging — no S3 yet, so callers can inspect the bytes
    # Package-name prefix MUST be preserved in zip entries so Agentic_Code_Loader
    # can extract + add one sys.path entry and still resolve
    # `import <package_name>.x.y`. Pre-v0.1.77 used add_folder__from_disk which
    # stripped the prefix — extracted zips were not actually importable by
    # package name. That went unnoticed because no Lambda consumed the S3 zip
    # yet ("S3-only until agentic image ships"). Now that the shim is generic
    # and sibling Lambdas will really boot from the zip, the fix matters.
    #
    # Implementation: add_files__from_disk(base_path, files, path_prefix) strips
    # `base_path` from each entry then re-adds `path_prefix`. Setting both to
    # `{name}/` keeps the prefix intact while letting us combine multiple
    # package trees in one zip.
    names = package_names or [PACKAGE_NAME]                                         # Default preserves the Playwright-only entrypoint; sibling apps pass e.g. ['sgraph_ai_service_playwright__cli', 'scripts']
    zb    = S3__Zip_Bytes(s3=S3())
    for name in names:
        files = list__match_regexes(files_list(name), SOURCE_FILE_REGEX)
        zb.add_files__from_disk(base_path=name, files_to_add=files, path_prefix=f'{name}/')
    return zb


def deploy_code(stage: str, app_name: str = DEFAULT_APP_NAME, version: str = None, region_name: str = None, package_names: list = None) -> dict:
    version      = version or str(version__sgraph_ai_service_playwright)
    bucket_name  = resolve_bucket_name(region_name)
    s3_key       = KEY_FORMAT.format(app_name=app_name, stage=stage, version=version)

    zb           = build_code_zip(package_names)
    zb.save_to_s3(bucket_name, s3_key)

    result = {'bucket'       : bucket_name         ,
              'key'          : s3_key              ,
              'app_name'     : app_name            ,
              'stage'        : stage               ,
              'version'      : version             ,
              'package_names': package_names or [PACKAGE_NAME],
              'bytes'        : len(zb.zip_bytes)    }                               # Size surfaced in CI logs — quick sanity check for accidental empty zips
    print(f'uploaded {result["bytes"]:,} bytes to s3://{bucket_name}/{s3_key}')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Package and upload a code zip to the agentic-bucket S3 layout.')
    parser.add_argument('--stage'   , required=True             , help="Deployment stage: 'dev', 'main', or 'prod'")
    parser.add_argument('--app-name', default=DEFAULT_APP_NAME  , help=f'App name (default: {DEFAULT_APP_NAME})')
    parser.add_argument('--version' , default=None              , help='Override version string (default: repo version file)')
    parser.add_argument('--region'  , default=None              , help='Override AWS region (default: boto3 session region)')
    parser.add_argument('--package' , action='append', default=None, dest='package_names', metavar='NAME',
                                                                   help=f'Folder name(s) to include in the zip. Repeatable. Default: {PACKAGE_NAME}')
    args = parser.parse_args()

    deploy_code(stage         = args.stage        ,
                app_name      = args.app_name     ,
                version       = args.version      ,
                region_name   = args.region       ,
                package_names = args.package_names)
    return 0


if __name__ == '__main__':
    sys.exit(main())
