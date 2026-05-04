# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/deploy_code.py (v0.1.29 — one-command agentic deploy)
#
# Scope (unit-level, no real AWS):
#   • module surface         — exposes deploy/main/constants.
#   • constants              — AGENTIC_* set / SG_PLAYWRIGHT__* strip lists match
#                               the v0.1.29 plan exactly.
#
# End-to-end bucket/upload/env-update/smoke verification lives in tests/deploy/.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from osbot_aws.AWS_Config                                                           import AWS_Config
from osbot_aws.aws.lambda_.Lambda                                                    import Lambda
from osbot_aws.aws.s3.S3                                                             import S3

from scripts                                                                        import deploy_code
from scripts                                                                        import package_code


class test_module_surface(TestCase):

    def test__exposes_expected_symbols(self):
        for attr in ('deploy'                 , 'ensure_bucket'           , 'upload_zip'               ,
                     'update_lambda_env'      , 'smoke_test'              , 'main'                     ,
                     'AGENTIC_ENV_VARS_TO_SET', 'LEGACY_ENV_VARS_TO_STRIP', 'SMOKE_TEST_TIMEOUT_SEC'   ):
            assert hasattr(deploy_code, attr), f'missing: {attr}'


class test_constants(TestCase):

    def test__agentic_env_vars_to_set_matches_plan(self):                           # Pointer trio per v0.1.29 plan §3
        assert deploy_code.AGENTIC_ENV_VARS_TO_SET == {'AGENTIC_APP_NAME'   ,
                                                       'AGENTIC_APP_STAGE'  ,
                                                       'AGENTIC_APP_VERSION'}

    def test__legacy_env_vars_to_strip_matches_plan(self):                          # v0.1.28-era loader vars — one-shot cutover per plan §1.2
        assert deploy_code.LEGACY_ENV_VARS_TO_STRIP == {'SG_PLAYWRIGHT__LAMBDA_NAME'    ,
                                                        'SG_PLAYWRIGHT__CODE_S3_VERSION',
                                                        'SG_PLAYWRIGHT__CODE_LOCAL_PATH',
                                                        'SG_PLAYWRIGHT__IMAGE_VERSION'  ,
                                                        'SG_PLAYWRIGHT__CODE_SOURCE'    }

    def test__smoke_timeout_is_positive(self):
        assert deploy_code.SMOKE_TEST_TIMEOUT_SEC > 0


class test_dependency_shape(TestCase):                                              # Regression guard — a missing method on S3/Lambda/AWS_Config shows up here, not on CI

    def test__aws_config_exposes_region_and_account_methods(self):                  # package_code.resolve_region + resolve_bucket_name call these
        cfg = AWS_Config()
        assert callable(cfg.region_name)
        assert callable(cfg.account_id )

    def test__s3_client_exposes_methods_used_by_deploy(self):                       # deploy_code.ensure_bucket calls these (NOT region_name — lives on AWS_Config)
        s3 = S3()
        assert callable(s3.bucket_exists)
        assert callable(s3.bucket_create)
        assert not hasattr(s3, 'region_name'), 'S3() has no region_name() — use AWS_Config().region_name() instead'

    def test__lambda_client_exposes_methods_used_by_deploy(self):                   # deploy_code.update_lambda_env + smoke_test call these
        lambda_obj = Lambda(name='any-name')                                        # Constructor is pure — doesn't hit AWS
        assert callable(lambda_obj.info                     )
        assert callable(lambda_obj.function_url             )
        assert callable(lambda_obj.set_env_variables        )
        assert callable(lambda_obj.update_lambda_configuration)


class test_resolve_region(TestCase):                                                # Pure function — no AWS if an explicit region is passed

    def test__explicit_region_short_circuits(self):
        assert package_code.resolve_region('eu-west-2') == 'eu-west-2'
