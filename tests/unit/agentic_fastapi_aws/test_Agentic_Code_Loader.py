# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Agentic_Code_Loader (v0.1.29)
#
# Scope (unit-level, no real AWS):
#   • load_from_local_path — AGENTIC_CODE_LOCAL_PATH override, directory validation
#   • load_from_s3          — AWS_REGION gate, env var precedence
#   • resolve_s3_bucket     — override > computed default
#   • resolve_s3_key        — override > computed from app/stage/version
#   • resolve               — precedence local > S3 > passthrough
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import tempfile
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Code_Loader           import (Agentic_Code_Loader,
                                                                                            DEFAULT_BUCKET_FORMAT,
                                                                                            DEFAULT_KEY_FORMAT   ,
                                                                                            PASSTHROUGH_TOKEN    )
from sgraph_ai_service_playwright.consts.env_vars                                   import (ENV_VAR__AGENTIC_APP_NAME              ,
                                                                                            ENV_VAR__AGENTIC_APP_STAGE             ,
                                                                                            ENV_VAR__AGENTIC_APP_VERSION           ,
                                                                                            ENV_VAR__AGENTIC_CODE_LOCAL_PATH       ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    ,
                                                                                            ENV_VAR__AWS_REGION                    )


ENV_KEYS = [ENV_VAR__AGENTIC_APP_NAME              ,
            ENV_VAR__AGENTIC_APP_STAGE             ,
            ENV_VAR__AGENTIC_APP_VERSION           ,
            ENV_VAR__AGENTIC_CODE_LOCAL_PATH       ,
            ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET ,
            ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    ,
            ENV_VAR__AWS_REGION                    ]


class _EnvScrub:                                                                    # Snapshot + restore the loader env vars
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k in ENV_KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class _SysPathSnapshot:                                                             # Loader mutates sys.path; put it back afterwards
    def __enter__(self):
        self.saved = list(sys.path)
        return self
    def __exit__(self, *exc):
        sys.path[:] = self.saved


class test_load_from_local_path(TestCase):

    def test__returns_none_when_env_unset(self):
        with _EnvScrub(), _SysPathSnapshot():
            assert Agentic_Code_Loader().load_from_local_path() is None

    def test__prepends_directory_and_returns_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _EnvScrub(**{ENV_VAR__AGENTIC_CODE_LOCAL_PATH: tmp}), _SysPathSnapshot():
                source = Agentic_Code_Loader().load_from_local_path()
                assert source      == f'local:{tmp}'
                assert sys.path[0] == tmp

    def test__raises_when_path_not_a_directory(self):
        with _EnvScrub(**{ENV_VAR__AGENTIC_CODE_LOCAL_PATH: '/nonexistent/xyzzy'}), _SysPathSnapshot():
            raised = False
            try:
                Agentic_Code_Loader().load_from_local_path()
            except RuntimeError as exc:
                raised = True
                assert '/nonexistent/xyzzy' in str(exc)
            assert raised, 'expected RuntimeError for missing directory'


class test_load_from_s3(TestCase):

    def test__returns_none_when_aws_region_unset(self):                             # Not on Lambda — skip S3
        with _EnvScrub(), _SysPathSnapshot():
            assert Agentic_Code_Loader().load_from_s3() is None

    def test__returns_none_when_local_path_set(self):                               # Local override wins
        with tempfile.TemporaryDirectory() as tmp:
            with _EnvScrub(**{ENV_VAR__AGENTIC_CODE_LOCAL_PATH: tmp,
                              ENV_VAR__AWS_REGION             : 'eu-west-2'}), _SysPathSnapshot():
                assert Agentic_Code_Loader().load_from_s3() is None

    def test__returns_none_on_lambda_without_agentic_app_name(self):                # Baseline variant: AWS_REGION is auto-set on Lambda but AGENTIC_APP_* are not pinned
        with _EnvScrub(**{ENV_VAR__AWS_REGION: 'eu-west-2'}), _SysPathSnapshot():
            assert Agentic_Code_Loader().load_from_s3() is None                     # Must fall through to passthrough, not KeyError on AGENTIC_APP_NAME

    def test__resolve_returns_passthrough_on_lambda_when_baseline(self):            # End-to-end: baseline Lambda should resolve cleanly to passthrough
        with _EnvScrub(**{ENV_VAR__AWS_REGION: 'eu-west-2'}), _SysPathSnapshot():
            assert Agentic_Code_Loader().resolve() == PASSTHROUGH_TOKEN


class test_resolve_s3_bucket(TestCase):

    def test__computes_default_from_account_and_region(self):
        with _EnvScrub():
            assert Agentic_Code_Loader().resolve_s3_bucket('123456789012', 'eu-west-2') \
                == DEFAULT_BUCKET_FORMAT.format(account_id='123456789012', region_name='eu-west-2')

    def test__honours_override_env_var(self):
        with _EnvScrub(**{ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET: 'custom-bucket'}):
            assert Agentic_Code_Loader().resolve_s3_bucket('123456789012', 'eu-west-2') == 'custom-bucket'


class test_resolve_s3_key(TestCase):

    def test__computes_key_from_app_stage_version(self):
        with _EnvScrub(**{ENV_VAR__AGENTIC_APP_NAME   : 'sg-playwright',
                          ENV_VAR__AGENTIC_APP_STAGE  : 'dev'          ,
                          ENV_VAR__AGENTIC_APP_VERSION: 'v0.1.29'      }):
            assert Agentic_Code_Loader().resolve_s3_key() \
                == DEFAULT_KEY_FORMAT.format(app_name='sg-playwright', stage='dev', version='v0.1.29')

    def test__honours_override_env_var(self):
        with _EnvScrub(**{ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY: 'custom/path.zip'}):
            assert Agentic_Code_Loader().resolve_s3_key() == 'custom/path.zip'

    def test__override_wins_over_computed(self):
        with _EnvScrub(**{ENV_VAR__AGENTIC_APP_NAME              : 'sg-playwright'    ,
                          ENV_VAR__AGENTIC_APP_STAGE             : 'dev'              ,
                          ENV_VAR__AGENTIC_APP_VERSION           : 'v0.1.29'          ,
                          ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    : 'custom/path.zip'  }):
            assert Agentic_Code_Loader().resolve_s3_key() == 'custom/path.zip'

    def test__returns_empty_string_when_required_env_var_missing(self):             # Soft-fail: without all three APP_NAME/STAGE/VERSION set, key can't be built — caller falls to passthrough
        with _EnvScrub(**{ENV_VAR__AGENTIC_APP_NAME : 'sg-playwright'}):
            assert Agentic_Code_Loader().resolve_s3_key() == ''
        with _EnvScrub(**{ENV_VAR__AGENTIC_APP_NAME  : 'sg-playwright',
                          ENV_VAR__AGENTIC_APP_STAGE : 'dev'          }):
            assert Agentic_Code_Loader().resolve_s3_key() == ''


class test_load_from_s3__soft_fail(TestCase):                                       # NoSuchKey + extraction errors fall through to passthrough so the Lambda still boots (baked code)

    def test__returns_none_when_s3_key_cannot_be_built(self):                       # APP_NAME set but VERSION missing — resolve_s3_key returns ''
        with _EnvScrub(**{ENV_VAR__AWS_REGION       : 'eu-west-2'     ,
                          ENV_VAR__AGENTIC_APP_NAME : 'sp-playwright-cli'}), _SysPathSnapshot():
            assert Agentic_Code_Loader().load_from_s3() is None

    def test__resolve_falls_to_passthrough_on_malformed_agentic_config(self):       # End-to-end: malformed agentic config MUST NOT raise
        with _EnvScrub(**{ENV_VAR__AWS_REGION       : 'eu-west-2'     ,
                          ENV_VAR__AGENTIC_APP_NAME : 'sp-playwright-cli'}), _SysPathSnapshot():
            assert Agentic_Code_Loader().resolve() == PASSTHROUGH_TOKEN


class test_resolve(TestCase):

    def test__passthrough_when_nothing_set(self):
        with _EnvScrub(), _SysPathSnapshot():
            assert Agentic_Code_Loader().resolve() == PASSTHROUGH_TOKEN

    def test__local_path_wins_over_aws_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _EnvScrub(**{ENV_VAR__AGENTIC_CODE_LOCAL_PATH: tmp,
                              ENV_VAR__AWS_REGION             : 'eu-west-2'}), _SysPathSnapshot():
                source = Agentic_Code_Loader().resolve()
                assert source.startswith('local:')
