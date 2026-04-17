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

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base
from sgraph_ai_service_playwright.docker.Lambda__Docker__SGraph_AI__Service__Playwright import (LAMBDA_ARCHITECTURE                            ,
                                                                                                 LAMBDA_MEMORY_MB                              ,
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


class _EnvScrub:
    KEYS = SG_PLAYWRIGHT_VARS
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
        with _EnvScrub(**{'SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER': 'X-Token'             ,
                          'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE' : 'secret'              ,
                          'SG_PLAYWRIGHT__SG_SEND_BASE_URL'   : 'https://send.example',
                          'SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'  : 'bootstrap'           ,
                          'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'  : 'sg-artefacts'        }):
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright().setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
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
        with _EnvScrub():                                                               # All unset
            lam  = Lambda__Docker__SGraph_AI__Service__Playwright().setup()
            fake = _Fake_Lambda_Function()
            lam.set_lambda_env_vars(fake)
        assert list(fake.env_vars.keys()) == ['SG_PLAYWRIGHT__DEPLOYMENT_TARGET']       # Only the pinned one
