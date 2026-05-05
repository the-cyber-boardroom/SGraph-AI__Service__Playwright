# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lambda__Docker__SGraph_AI__Service__Playwright
#
# Shape + tuning constants + env-var propagation logic. Does NOT invoke real
# Lambda APIs (that's the deploy test under tests/deploy/).
#
# `set_lambda_env_vars()` is exercised against a stub `lambda_function` that
# records every set_env_variable() call — lets us assert:
#   • every SG_PLAYWRIGHT__* env var declared in CI is propagated
#   • DEPLOYMENT_TARGET is pinned to 'lambda' regardless of host env
#   • empty/unset values are skipped (won't overwrite Lambda defaults with blanks)
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                           import TestCase

from sg_compute_specs.playwright.core.consts.version                                        import version__sgraph_ai_service_playwright
from sg_compute_specs.playwright.core.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base
from sg_compute_specs.playwright.core.docker.Lambda__Docker__SGraph_AI__Service__Playwright import (APP_NAME                                       ,
                                                                                                 LAMBDA_ARCHITECTURE                            ,
                                                                                                 LAMBDA_MEMORY_MB                              ,
                                                                                                 VARIANT__AGENTIC                               ,
                                                                                                 VARIANT__BASELINE                              ,
                                                                                                 VARIANTS__ALL                                  ,
                                                                                                 Lambda__Docker__SGraph_AI__Service__Playwright)


class _Fake_Lambda_Function:                                                            # Record-only stub; no AWS calls
    def __init__(self):
        self.env_vars = {}
    def set_env_variable(self, key, value):
        self.env_vars[key] = value


SG_PLAYWRIGHT_VARS = ['SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER',
                      'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE' ,
                      'SG_PLAYWRIGHT__SG_SEND_BASE_URL'   ,
                      'SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'  ,
                      'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'  ,
                      'SG_PLAYWRIGHT__DEPLOYMENT_TARGET'  ]

FAST_API_AUTH_VARS = ['FAST_API__AUTH__API_KEY__NAME' ,
                      'FAST_API__AUTH__API_KEY__VALUE']


class _EnvScrub:
    KEYS = SG_PLAYWRIGHT_VARS + FAST_API_AUTH_VARS
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k in self.KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in self.KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class test_module_constants(TestCase):

    def test__production_tuning(self):
        assert LAMBDA_MEMORY_MB    == 5120                                              # Lower values hit OOM on real sequences
        assert LAMBDA_ARCHITECTURE == 'x86_64'                                          # GH Actions x86_64 runners


class test_class_shape(TestCase):

    def test__is_subclass_of_base(self):
        assert issubclass(Lambda__Docker__SGraph_AI__Service__Playwright,
                          Docker__SGraph_AI__Service__Playwright__Base)

    def test__method_surface(self):
        for method in ('create_lambda', 'set_lambda_env_vars' , 'create_lambda_function_url',
                       'update_lambda_function', 'function_url'):
            assert callable(getattr(Lambda__Docker__SGraph_AI__Service__Playwright, method)), \
                   f'missing method: {method}'


class test_set_lambda_env_vars(TestCase):

    def test__propagates_all_declared_vars_when_all_present(self):
        with _EnvScrub(**{'FAST_API__AUTH__API_KEY__NAME'     : 'X-API-Key'           ,
                          'FAST_API__AUTH__API_KEY__VALUE'    : 'api-secret'          ,
                          'SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER': 'X-Token'             ,
                          'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE' : 'secret'              ,
                          'SG_PLAYWRIGHT__SG_SEND_BASE_URL'   : 'https://send.example',
                          'SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'  : 'bootstrap'           ,
                          'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'  : 'sg-artefacts'        }):
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright().setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        assert fake.env_vars['FAST_API__AUTH__API_KEY__NAME'     ] == 'X-API-Key'
        assert fake.env_vars['FAST_API__AUTH__API_KEY__VALUE'    ] == 'api-secret'
        assert fake.env_vars['SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER'] == 'X-Token'
        assert fake.env_vars['SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE' ] == 'secret'
        assert fake.env_vars['SG_PLAYWRIGHT__SG_SEND_BASE_URL'   ] == 'https://send.example'
        assert fake.env_vars['SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'  ] == 'bootstrap'
        assert fake.env_vars['SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'  ] == 'sg-artefacts'
        assert fake.env_vars['SG_PLAYWRIGHT__DEPLOYMENT_TARGET'  ] == 'lambda'

    def test__pins_deployment_target_to_lambda_even_when_host_env_differs(self):
        with _EnvScrub(**{'SG_PLAYWRIGHT__DEPLOYMENT_TARGET': 'laptop'}):               # Host env says laptop
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright().setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        assert fake.env_vars['SG_PLAYWRIGHT__DEPLOYMENT_TARGET'] == 'lambda'            # Still pinned

    def test__skips_unset_or_empty_env_vars(self):                                      # Don't overwrite Lambda defaults with blanks
        with _EnvScrub():                                                               # All SG_* + FAST_API__* unset
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__BASELINE).setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        assert list(fake.env_vars.keys()) == ['SG_PLAYWRIGHT__DEPLOYMENT_TARGET']       # Baseline pins only DEPLOYMENT_TARGET — no AGENTIC_APP_* trio


class test_variants(TestCase):

    def test__default_variant_is_agentic(self):                                         # Default variant hot-swaps from S3 on every invocation
        lam = Lambda__Docker__SGraph_AI__Service__Playwright()
        assert lam.variant == VARIANT__AGENTIC

    def test__variants_all_has_baseline_and_agentic(self):                              # Source of truth for provision_lambdas.py iteration
        assert set(VARIANTS__ALL) == {VARIANT__BASELINE, VARIANT__AGENTIC}

    def test__lambda_names_per_variant(self):
        agentic  = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__AGENTIC , stage='dev').setup()
        baseline = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__BASELINE, stage='dev').setup()
        assert agentic .lambda_name() == 'sg-playwright-dev'                            # Agentic = the primary name (matches scripts/deploy_code.py --update-lambda target)
        assert baseline.lambda_name() == 'sg-playwright-baseline-dev'                   # Baseline = explicit 'baseline' segment so the two never collide

    def test__lambda_names_per_stage(self):                                             # Stage suffix plumbed through both variants
        for stage in ('dev', 'main', 'prod'):
            agentic  = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__AGENTIC , stage=stage).setup()
            baseline = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__BASELINE, stage=stage).setup()
            assert agentic .lambda_name() == f'{APP_NAME}-{stage}'
            assert baseline.lambda_name() == f'{APP_NAME}-baseline-{stage}'

    def test__unknown_variant_raises(self):                                             # Fail fast — don't create a wrongly-named Lambda
        with self.assertRaises(ValueError) as ctx:
            Lambda__Docker__SGraph_AI__Service__Playwright(variant='unknown').setup()
        assert "unknown variant 'unknown'" in str(ctx.exception)

    def test__agentic_variant_pins_AGENTIC_APP_trio(self):
        with _EnvScrub():                                                               # All SG_* + FAST_API__* unset so only pinned vars land on the stub
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__AGENTIC, stage='dev').setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        assert fake.env_vars['AGENTIC_APP_NAME'   ] == APP_NAME                         # The boot shim reads these three to resolve s3://<bucket>/apps/<app>/<stage>/v<X.Y.Z>.zip
        assert fake.env_vars['AGENTIC_APP_STAGE'  ] == 'dev'
        assert fake.env_vars['AGENTIC_APP_VERSION'] == str(version__sgraph_ai_service_playwright)

    def test__baseline_variant_does_NOT_pin_AGENTIC_APP_trio(self):                     # Baseline relies on baked code in the image (code_source=passthrough:sys.path)
        with _EnvScrub():
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__BASELINE, stage='dev').setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        for key in ('AGENTIC_APP_NAME', 'AGENTIC_APP_STAGE', 'AGENTIC_APP_VERSION'):
            assert key not in fake.env_vars, f'baseline variant must not set {key}'

    def test__agentic_version_matches_repo_version_file(self):                          # Sanity — the Lambda and the S3 zip MUST agree on the version (or the shim 404s on download)
        with _EnvScrub():
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright(variant=VARIANT__AGENTIC, stage='dev').setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        assert fake.env_vars['AGENTIC_APP_VERSION'] == str(version__sgraph_ai_service_playwright)
