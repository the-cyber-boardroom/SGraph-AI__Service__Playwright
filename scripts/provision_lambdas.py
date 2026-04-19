# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — provision_lambdas.py (v0.1.31 — two-Lambda provisioning)
#
# Upserts the two dev/stage Lambdas side-by-side from the same ECR image:
#
#   • sg-playwright-baseline-<stage> — boots the baked code in the image
#     (Agentic_Code_Loader returns `passthrough:sys.path`). Always-available
#     fallback; proves the image boots cleanly without S3 overlay.
#   • sg-playwright-<stage>          — pins AGENTIC_APP_NAME / _STAGE /
#     _VERSION so the boot shim downloads the zip from S3 and overlays
#     sys.path (code_source reads `s3:<bucket>/apps/<app>/<stage>/vX.Y.Z.zip`).
#
# Idempotent: re-running updates the image + env vars in place without
# touching the Function URL host UUID (CloudFront origin).
#
# Called from:
#   • Day-5 CI: the `provision-lambdas` job (runs after build-and-push-image
#     and deploy-code both succeed).
#   • Local operators: one-shot bootstrap on a fresh account.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import (Lambda__Docker__SGraph_AI__Service__Playwright,
                                                                                                VARIANTS__ALL                                  )


def provision_variant(variant: str, stage: str, wait_for_active: bool = True) -> dict:
    wrapper = Lambda__Docker__SGraph_AI__Service__Playwright(variant=variant, stage=stage).setup()
    result  = wrapper.create_lambda(wait_for_active=wait_for_active)

    function_url_value = (result.get('function_url') or {}).get('function_url')
    print(f'provisioned {variant:8s} Lambda: {wrapper.lambda_name()} -> {function_url_value}')
    return {'variant'      : variant                            ,
            'lambda_name'  : wrapper.lambda_name()              ,
            'function_url' : function_url_value                 ,
            'create_result': result.get('create_result')        }


def provision(stage: str, wait_for_active: bool = True) -> dict:
    results = {}
    for variant in VARIANTS__ALL:                                                       # Baseline first so it's up before the agentic Lambda tries to load from S3
        results[variant] = provision_variant(variant=variant, stage=stage, wait_for_active=wait_for_active)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Provision the two Playwright Lambdas (baseline + agentic) from the current ECR image.')
    parser.add_argument('--stage'   , required=True        , help="Deployment stage: 'dev', 'main', or 'prod'")
    parser.add_argument('--no-wait' , action='store_true'  , help='Skip waiting for Lambda state=Active after create/update')
    args = parser.parse_args()

    provision(stage=args.stage, wait_for_active=not args.no_wait)
    return 0


if __name__ == '__main__':
    sys.exit(main())
