# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__SP__CLI configuration
# No AWS — asserts the Type_Safe instance carries the expected Lambda shape
# (name, memory, timeout, handler path) before any network call happens.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.deploy.Enum__Lambda__Variant                                                       import Enum__Lambda__Variant
from sgraph_ai_service_playwright__cli.deploy.Lambda__SP__CLI                                                              import (Lambda__SP__CLI         ,
                                                                                                                                APP_NAME                 ,
                                                                                                                                LAMBDA_HANDLER            ,
                                                                                                                                LAMBDA_MEMORY_MB          ,
                                                                                                                                LAMBDA_TIMEOUT_SECS       ,
                                                                                                                                LAMBDA_ARCHITECTURE       )


ROLE_ARN  = 'arn:aws:iam::745506449035:role/sp-playwright-cli-lambda'
IMAGE_URI = '745506449035.dkr.ecr.eu-west-2.amazonaws.com/sp-playwright-cli:latest'


class _FakeLambdaFunction:                                                          # Captures set_env_variable calls so the test can assert what was sent
    def __init__(self):
        self.env = {}
    def set_env_variable(self, key, value):
        self.env[key] = value


class test_Lambda__SP__CLI(TestCase):

    def test__default_variant_is_agentic(self):                                     # AGENTIC is the default — preserves the existing single-Lambda deployment name
        with Lambda__SP__CLI(stage='dev', role_arn=ROLE_ARN, image_uri=IMAGE_URI) as _:
            assert _.variant       == Enum__Lambda__Variant.AGENTIC
            assert _.lambda_name() == f'{APP_NAME}-dev'

    def test__baseline_variant_name(self):
        lam = Lambda__SP__CLI(stage='dev', variant=Enum__Lambda__Variant.BASELINE, role_arn=ROLE_ARN, image_uri=IMAGE_URI)
        assert lam.lambda_name() == f'{APP_NAME}-baseline-dev'

    def test__agentic_variant_name_omits_baseline_segment(self):                    # Baseline gets the explicit '-baseline-' segment; agentic does NOT
        lam = Lambda__SP__CLI(stage='prod', variant=Enum__Lambda__Variant.AGENTIC, role_arn=ROLE_ARN, image_uri=IMAGE_URI)
        assert lam.lambda_name()           == f'{APP_NAME}-prod'
        assert 'baseline' not in lam.lambda_name()

    def test__handler_path_matches_module(self):                                    # The image CMD + this string must match exactly
        assert LAMBDA_HANDLER == 'sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler'

    def test__tuning_defaults(self):                                                # Smoke-check the sizing so regressions are loud
        assert LAMBDA_MEMORY_MB     == 1024                                         # Adapter Lambda — no browser
        assert LAMBDA_TIMEOUT_SECS  == 120                                          # sp create is ~60s, buffer 2x
        assert LAMBDA_ARCHITECTURE  == 'x86_64'                                     # Base image is x86_64

    def test__set_env_vars__agentic_sets_pin_trio(self):                            # AGENTIC: the boot shim reads these to resolve the S3 zip
        lam = Lambda__SP__CLI(stage='dev', variant=Enum__Lambda__Variant.AGENTIC,
                              role_arn=ROLE_ARN, image_uri=IMAGE_URI, version='v0.1.5')
        fake = _FakeLambdaFunction()
        lam.set_env_vars(fake)
        assert fake.env.get('AGENTIC_APP_NAME'   ) == APP_NAME
        assert fake.env.get('AGENTIC_APP_STAGE'  ) == 'dev'
        assert fake.env.get('AGENTIC_APP_VERSION') == 'v0.1.5'

    def test__set_env_vars__baseline_omits_pin_trio(self):                          # BASELINE: handler detects absence and boots from baked image
        lam = Lambda__SP__CLI(stage='dev', variant=Enum__Lambda__Variant.BASELINE, role_arn=ROLE_ARN, image_uri=IMAGE_URI)
        fake = _FakeLambdaFunction()
        lam.set_env_vars(fake)
        assert 'AGENTIC_APP_NAME'    not in fake.env
        assert 'AGENTIC_APP_STAGE'   not in fake.env
        assert 'AGENTIC_APP_VERSION' not in fake.env
