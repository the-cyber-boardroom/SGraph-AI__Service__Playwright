# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__SP__CLI configuration
# No AWS — asserts the Type_Safe instance carries the expected Lambda shape
# (name, memory, timeout, handler path) before any network call happens.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.deploy.Lambda__SP__CLI                                                              import (Lambda__SP__CLI         ,
                                                                                                                                APP_NAME                 ,
                                                                                                                                LAMBDA_HANDLER            ,
                                                                                                                                LAMBDA_MEMORY_MB          ,
                                                                                                                                LAMBDA_TIMEOUT_SECS       ,
                                                                                                                                LAMBDA_ARCHITECTURE       )


ROLE_ARN  = 'arn:aws:iam::745506449035:role/sp-playwright-cli-lambda'
IMAGE_URI = '745506449035.dkr.ecr.eu-west-2.amazonaws.com/sp-playwright-cli:latest'


class test_Lambda__SP__CLI(TestCase):

    def test__init__and_lambda_name(self):
        with Lambda__SP__CLI(stage='dev', role_arn=ROLE_ARN, image_uri=IMAGE_URI) as _:
            assert _.lambda_name() == f'{APP_NAME}-dev'
            assert str(_.role_arn)  == ROLE_ARN
            assert str(_.image_uri) == IMAGE_URI

    def test__lambda_name_includes_stage(self):
        assert Lambda__SP__CLI(stage='prod', role_arn=ROLE_ARN, image_uri=IMAGE_URI).lambda_name() == f'{APP_NAME}-prod'

    def test__handler_path_matches_module(self):                                    # The image CMD + this string must match exactly
        assert LAMBDA_HANDLER == 'sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler'

    def test__tuning_defaults(self):                                                # Smoke-check the sizing so regressions are loud
        assert LAMBDA_MEMORY_MB     == 1024                                         # Adapter Lambda — no browser
        assert LAMBDA_TIMEOUT_SECS  == 120                                          # sp create is ~60s, buffer 2x
        assert LAMBDA_ARCHITECTURE  == 'x86_64'                                     # Base image is x86_64
