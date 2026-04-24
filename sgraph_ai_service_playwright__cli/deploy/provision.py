# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Deploy orchestrator
# Runs the full provision chain for the SP CLI Lambda, in order:
#
#   1. SP__CLI__Lambda__Role.ensure()     — create/update execution role
#   2. Docker__SP__CLI.build_and_push()   — build image, push to ECR
#   3. Lambda__SP__CLI.upsert()           — create/update Lambda, wire URL
#
# Idempotent — safe to re-run on every deploy. Prints the Function URL on
# success so CI / GH Actions / local operators see it.
#
# Run:
#   python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.deploy.Docker__SP__CLI                       import Docker__SP__CLI
from sgraph_ai_service_playwright__cli.deploy.Lambda__SP__CLI                       import Lambda__SP__CLI
from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Role                 import SP__CLI__Lambda__Role


class Provision__SP__CLI(Type_Safe):

    def run(self, stage: str, wait_for_active: bool = True) -> dict:
        role_result   = SP__CLI__Lambda__Role().ensure()
        docker_result = Docker__SP__CLI().setup().build_and_push()
        lambda_result = Lambda__SP__CLI(stage     = stage                 ,
                                        role_arn  = role_result['role_arn'],
                                        image_uri = docker_result['image_uri']).upsert(wait_for_active=wait_for_active)
        return {'role'   : role_result  ,
                'docker' : docker_result,
                'lambda' : lambda_result}


def main() -> int:
    parser = argparse.ArgumentParser(description='Provision the SP CLI management Lambda (role → image → function).')
    parser.add_argument('--stage'   , required=True        , help='Deployment stage (e.g. dev, prod)')
    parser.add_argument('--no-wait' , action='store_true'  , help='Skip waiting for Lambda state=Active')
    args   = parser.parse_args()

    result = Provision__SP__CLI().run(stage=args.stage, wait_for_active=not args.no_wait)

    function_url = (result.get('lambda') or {}).get('function_url', {}).get('function_url')
    print(f'\n✅ SP CLI Lambda provisioned: {function_url}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
