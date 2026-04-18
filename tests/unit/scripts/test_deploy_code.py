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

from scripts                                                                        import deploy_code


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
