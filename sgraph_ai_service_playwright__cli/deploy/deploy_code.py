# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Deploy__SP__CLI__Code
# Packages the SP CLI Python source into a zip and uploads it to S3, matching
# the layout Agentic_Code_Loader expects:
#
#   s3://{account}--sgraph-ai--{region}/apps/sp-playwright-cli/{stage}/{version}.zip
#
# Optionally flips AGENTIC_APP_VERSION on the agentic Lambda so the next cold
# start picks up the new zip. That env-flip is the hot-swap — no image
# rebuild, no full provision chain. Target round-trip ~10 s.
#
# Packages included in the zip:
#   • sgraph_ai_service_playwright__cli  — the Type_Safe service + routes + deploy helpers
#   • scripts                            — provision_ec2 + observability (imported lazily by Ec2__Service)
#
# Version source: sgraph_ai_service_playwright__cli/version (single-line file).
# Override via --version VX.Y.Z. Uploads are IMMUTABLE — bump the version file
# for every code change that should be rolled to the Lambda.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys
from pathlib                                                                        import Path

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.utils.Files                                                        import file_contents

from sgraph_ai_service_playwright__cli.deploy.Lambda__SP__CLI                       import APP_NAME as SP_CLI_APP_NAME
from scripts.deploy_code                                                            import deploy as deploy_code__deploy


PACKAGE_NAMES          = ['sgraph_ai_service_playwright__cli', 'scripts']           # Two trees included in the zip (see module header)
VERSION_FILE_RELATIVE  = 'sgraph_ai_service_playwright__cli/version'                # Single-line file — one version string per line


def read_version() -> str:                                                          # Reads the SP CLI version file from the repo root; falls back to 'v0.0.1' if missing
    repo_root = Path(__file__).resolve().parents[2]
    path      = repo_root / VERSION_FILE_RELATIVE
    if not path.is_file():
        return 'v0.0.1'
    return (file_contents(str(path)) or '').strip() or 'v0.0.1'


class Deploy__SP__CLI__Code(Type_Safe):

    def run(self, stage         : str         ,
                  version       : str  = ''    ,                                    # Empty → read from sgraph_ai_service_playwright__cli/version
                  region_name   : str  = ''    ,                                    # Empty → AWS_DEFAULT_REGION env / boto3 session
                  update_lambda : bool = False ,                                    # True → flip AGENTIC_APP_VERSION on sp-playwright-cli-{stage}
                  smoke         : bool = False                                      # Ignored without --update-lambda
             ) -> dict:
        version      = version or read_version()
        lambda_name  = f'{SP_CLI_APP_NAME}-{stage}'                                 # Agentic variant — the one that reads AGENTIC_APP_* env vars
        result = deploy_code__deploy(stage         = stage            ,
                                      app_name      = SP_CLI_APP_NAME  ,
                                      lambda_name   = lambda_name      ,
                                      version       = version          ,
                                      region_name   = region_name or None,
                                      update_lambda = update_lambda    ,
                                      smoke         = smoke            ,
                                      package_names = PACKAGE_NAMES    )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Package the SP CLI source, upload to S3, and optionally flip AGENTIC_APP_VERSION on the agentic Lambda.')
    parser.add_argument('--stage'        , required=True      , help='Deployment stage (e.g. dev, prod)')
    parser.add_argument('--version'      , default=''         , help='Override version string (default: sgraph_ai_service_playwright__cli/version)')
    parser.add_argument('--region'       , default=''         , help='Override AWS region (default: boto3 session region)')
    parser.add_argument('--update-lambda', action='store_true', help='Flip AGENTIC_APP_VERSION on sp-playwright-cli-{stage} after the upload')
    parser.add_argument('--smoke'        , action='store_true', help='After --update-lambda, probe /admin/health to verify code_source')
    args = parser.parse_args()

    result = Deploy__SP__CLI__Code().run(stage         = args.stage         ,
                                          version       = args.version       ,
                                          region_name   = args.region        ,
                                          update_lambda = args.update_lambda ,
                                          smoke         = args.smoke         )

    print(f'\n✅ SP CLI code uploaded: s3://{result.get("bucket")}/{result.get("key")} '
          f'({result.get("bytes"):,} bytes, version={result.get("version")})')
    if result.get('env_update'):
        print(f'✅ Lambda env flipped on {result["lambda_name"]}: {result["env_update"]["set"]}')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
