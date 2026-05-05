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
# Modes:
#   • --mode=full       — default. Upserts both variants (image + env vars).
#                         Use when the Docker image was rebuilt (new deps, new
#                         shim, first deploy).
#   • --mode=code-only  — Python-only path. Skips baseline entirely and only
#                         refreshes env vars on the agentic variant (which pins
#                         AGENTIC_APP_VERSION → the S3 zip key). Drops the
#                         ~30-60s update_function_code image-pull wait.
#
# Idempotent: re-running in either mode updates in place without touching the
# Function URL host UUID (CloudFront origin).
#
# Called from:
#   • Day-5 CI: the `provision-lambdas` job picks the mode from the
#     `build-and-push-image` job result — success = full, skipped = code-only.
#   • Local operators: one-shot bootstrap on a fresh account (use --mode=full).
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

from sg_compute_specs.playwright.core.docker.Lambda__Docker__SGraph_AI__Service__Playwright import (Lambda__Docker__SGraph_AI__Service__Playwright,
                                                                                                MODE__CODE_ONLY                                ,
                                                                                                MODE__FULL                                     ,
                                                                                                MODES__ALL                                     ,
                                                                                                VARIANT__AGENTIC                               ,
                                                                                                VARIANTS__ALL                                  )


def provision_variant(variant: str, stage: str, wait_for_active: bool = True, mode: str = MODE__FULL) -> dict:
    wrapper = Lambda__Docker__SGraph_AI__Service__Playwright(variant=variant, stage=stage).setup()
    if mode == MODE__CODE_ONLY:
        result = wrapper.update_lambda_code_only()
    else:
        result = wrapper.create_lambda(wait_for_active=wait_for_active)

    function_url_value = (result.get('function_url') or {}).get('function_url')
    print(f'provisioned {variant:8s} Lambda [{mode:10s}]: {wrapper.lambda_name()} -> {function_url_value}')
    return {'variant'      : variant                            ,
            'lambda_name'  : wrapper.lambda_name()              ,
            'function_url' : function_url_value                 ,
            'mode'         : mode                               ,
            'create_result': result.get('create_result')        }


def provision(stage: str, wait_for_active: bool = True, mode: str = MODE__FULL) -> dict:
    if mode not in MODES__ALL:
        raise ValueError(f'unknown mode {mode!r}; expected one of {MODES__ALL}')

    if mode == MODE__CODE_ONLY:                                                         # Baseline bakes code into the image — env-var refresh changes nothing there, so skip it entirely
        return {VARIANT__AGENTIC: provision_variant(variant=VARIANT__AGENTIC, stage=stage, wait_for_active=wait_for_active, mode=mode)}

    results = {}
    for variant in VARIANTS__ALL:                                                       # Baseline first so the always-available fallback is up before the agentic Lambda tries to load from S3
        results[variant] = provision_variant(variant=variant, stage=stage, wait_for_active=wait_for_active, mode=mode)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Provision the two Playwright Lambdas (baseline + agentic) from the current ECR image.')
    parser.add_argument('--stage'   , required=True        , help="Deployment stage: 'dev', 'main', or 'prod'")
    parser.add_argument('--no-wait' , action='store_true'  , help='Skip waiting for Lambda state=Active after create/update')
    parser.add_argument('--mode'    , default=MODE__FULL   , choices=MODES__ALL, help='full = upsert both variants (image + env vars); code-only = refresh AGENTIC_APP_VERSION on agentic only (skips ~30s image-pull wait)')
    args = parser.parse_args()

    provision(stage=args.stage, wait_for_active=not args.no_wait, mode=args.mode)
    return 0


if __name__ == '__main__':
    sys.exit(main())
