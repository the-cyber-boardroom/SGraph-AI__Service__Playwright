# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Deploy orchestrator
# Runs the full provision chain for the SP CLI Lambda(s), in order:
#
#   0. CI__User__Passrole.ensure()        — grant iam:PassRole on the Lambda
#                                           role to the CI user (idempotent
#                                           after the first run)
#   1. SP__CLI__Lambda__Role.ensure()     — create/update execution role
#   2. Docker__SP__CLI.build_and_push()   — build image, push to ECR
#                                           (skipped in CI via --skip-build)
#   3. Lambda__SP__CLI.upsert()           — create/update each variant +
#                                           wire its Function URL.
#
# Two variants per stage (commit 3 of the hot-swap series):
#
#   • baseline (sp-playwright-cli-baseline-{stage})
#       Boots the baked image directly. Always-available rollback path.
#   • agentic  (sp-playwright-cli-{stage})
#       AGENTIC_APP_NAME / STAGE / VERSION env vars set; lambda_handler
#       routes through Agentic_Boot_Shim → loads code from S3 zip.
#
# Pass --variant to provision only one of them. Default = both, in order
# (baseline first so a failure leaves a known-good function in place).
#
# Run:
#   python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev                 (local — full chain, both variants)
#   python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev --skip-build    (CI — role + Lambdas only)
#   python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev --variant agentic   (one variant)
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.deploy.CI__User__Passrole                    import CI__User__Passrole
from sgraph_ai_service_playwright__cli.deploy.Docker__SP__CLI                       import Docker__SP__CLI
from sgraph_ai_service_playwright__cli.deploy.Enum__Lambda__Variant                 import Enum__Lambda__Variant
from sgraph_ai_service_playwright__cli.deploy.Lambda__SP__CLI                       import Lambda__SP__CLI
from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Role                 import SP__CLI__Lambda__Role


VARIANTS_DEFAULT_ORDER = (Enum__Lambda__Variant.BASELINE, Enum__Lambda__Variant.AGENTIC)   # Baseline first — keeps a known-good function alive while the agentic upsert runs


class Provision__SP__CLI(Type_Safe):

    def run(self, stage           : str                                          ,
                  skip_build      : bool   = False                                ,   # CI flips this on when the prior job already built + pushed
                  wait_for_active : bool   = True                                 ,
                  variants        : tuple  = VARIANTS_DEFAULT_ORDER                ,   # Allow narrowing to one variant for incremental ops
                  version         : str    = ''                                       # Required for AGENTIC; ignored for BASELINE
             ) -> dict:
        passrole_result = CI__User__Passrole().ensure()                              # Step 0 — without iam:PassRole on the Lambda role, lambda.CreateFunction fails AccessDenied
        print(f'[provision] passrole: {passrole_result}')

        role_result     = SP__CLI__Lambda__Role().ensure()
        docker_result   = self.resolve_image(skip_build)

        lambda_results  = {}
        for variant in variants:
            print(f'[provision] upserting variant={variant}')
            lambda_results[str(variant)] = Lambda__SP__CLI(stage     = stage                 ,
                                                           variant   = variant                ,
                                                           role_arn  = role_result['role_arn'],
                                                           image_uri = docker_result['image_uri'],
                                                           version   = version                ).upsert(wait_for_active=wait_for_active)

        return {'passrole': passrole_result,
                'role'    : role_result    ,
                'docker'  : docker_result  ,
                'lambdas' : lambda_results }

    def resolve_image(self, skip_build: bool) -> dict:
        if skip_build:                                                              # Just compute the URI — no setup, no osbot-docker, no daemon
            return {'image_uri': Docker__SP__CLI().image_uri(),
                    'skipped'  : True                         }
        return Docker__SP__CLI().setup().build_and_push()


def parse_variants(value: str) -> tuple:                                            # 'both' (default) | 'baseline' | 'agentic'
    if not value or value == 'both':
        return VARIANTS_DEFAULT_ORDER
    return (Enum__Lambda__Variant(value),)


def main() -> int:
    parser = argparse.ArgumentParser(description='Provision the SP CLI management Lambda(s) (role → image → function).')
    parser.add_argument('--stage'      , required=True      , help='Deployment stage (e.g. dev, prod)')
    parser.add_argument('--skip-build' , action='store_true', help='Skip build+push; assume the image is already at <ecr-repo>:latest (CI mode)')
    parser.add_argument('--no-wait'    , action='store_true', help='Skip waiting for Lambda state=Active')
    parser.add_argument('--variant'    , default='both'     , choices=['both', 'baseline', 'agentic'],
                                                              help='Provision one variant or both (default: both)')
    parser.add_argument('--version'    , default=''         , help='Pin AGENTIC_APP_VERSION on the agentic Lambda (e.g. v0.0.5). Defaults to v0.0.1 fallback when empty.')
    args   = parser.parse_args()

    result = Provision__SP__CLI().run(stage           = args.stage              ,
                                       skip_build      = args.skip_build         ,
                                       wait_for_active = not args.no_wait        ,
                                       variants        = parse_variants(args.variant),
                                       version         = args.version            )

    print('\n✅ SP CLI Lambda(s) provisioned:')
    for variant_name, lambda_result in (result.get('lambdas') or {}).items():
        url = (lambda_result or {}).get('function_url', {}).get('function_url')
        print(f'   {variant_name:>9}  {url}')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
