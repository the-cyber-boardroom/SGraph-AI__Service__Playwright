# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Deploy orchestrator
# Runs the full provision chain for the SP CLI Lambda, in order:
#
#   0. CI__User__Passrole.ensure()        — grant iam:PassRole on the Lambda
#                                           role to the CI user (one-time;
#                                           idempotent afterwards)
#   1. SP__CLI__Lambda__Role.ensure()     — create/update execution role
#   2. Docker__SP__CLI.build_and_push()   — build image, push to ECR
#   3. Lambda__SP__CLI.upsert()           — create/update Lambda, wire URL
#
# Idempotent — safe to re-run on every deploy. Prints the Function URL on
# success so CI / GH Actions / local operators see it.
#
# CI split: the GH Actions workflow runs step 2 in its own job (so image
# rebuilds are cached / skipped independently) and then runs this
# orchestrator with --skip-build so steps 0, 1, 3 execute against the
# already-published image. --skip-build also avoids pulling in osbot-docker
# on the provision job, keeping its install list minimal.
#
# Run:
#   python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev                 (local — full chain, needs Docker daemon)
#   python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev --skip-build    (CI — role + Lambda only)
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.deploy.CI__User__Passrole                    import CI__User__Passrole
from sgraph_ai_service_playwright__cli.deploy.Docker__SP__CLI                       import Docker__SP__CLI
from sgraph_ai_service_playwright__cli.deploy.Lambda__SP__CLI                       import Lambda__SP__CLI
from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Role                 import SP__CLI__Lambda__Role


class Provision__SP__CLI(Type_Safe):

    def run(self, stage           : str                          ,
                  skip_build      : bool                = False  ,                  # CI flips this on when the prior job already built + pushed
                  wait_for_active : bool                = True
             ) -> dict:
        passrole_result = CI__User__Passrole().ensure()                             # Bootstrap: without iam:PassRole on the Lambda role, lambda.CreateFunction fails with AccessDenied (see ci pass #7 for the original symptom)
        print(f'[provision] passrole: {passrole_result}')

        role_result     = SP__CLI__Lambda__Role().ensure()
        docker_result   = self.resolve_image(skip_build)
        lambda_result   = Lambda__SP__CLI(stage     = stage                 ,
                                          role_arn  = role_result['role_arn'],
                                          image_uri = docker_result['image_uri']).upsert(wait_for_active=wait_for_active)
        return {'passrole': passrole_result,
                'role'    : role_result    ,
                'docker'  : docker_result  ,
                'lambda'  : lambda_result  }

    def resolve_image(self, skip_build: bool) -> dict:
        if skip_build:                                                              # Just compute the URI — no setup, no osbot-docker, no daemon
            return {'image_uri': Docker__SP__CLI().image_uri(),
                    'skipped'  : True                         }
        return Docker__SP__CLI().setup().build_and_push()


def main() -> int:
    parser = argparse.ArgumentParser(description='Provision the SP CLI management Lambda (role → image → function).')
    parser.add_argument('--stage'      , required=True      , help='Deployment stage (e.g. dev, prod)')
    parser.add_argument('--skip-build' , action='store_true', help='Skip build+push; assume the image is already at <ecr-repo>:latest (CI mode)')
    parser.add_argument('--no-wait'    , action='store_true', help='Skip waiting for Lambda state=Active')
    args   = parser.parse_args()

    result = Provision__SP__CLI().run(stage           = args.stage         ,
                                       skip_build      = args.skip_build    ,
                                       wait_for_active = not args.no_wait   )

    function_url = (result.get('lambda') or {}).get('function_url', {}).get('function_url')
    print(f'\n✅ SP CLI Lambda provisioned: {function_url}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
