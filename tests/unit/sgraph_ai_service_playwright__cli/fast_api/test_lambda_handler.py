# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for fast_api/lambda_handler.py
# Covers the boot-mode selector (is_agentic_mode) without actually triggering
# the agentic boot path (which would touch S3). The agentic path itself is
# covered by tests on Agentic_Boot_Shim.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.fast_api                              import lambda_handler


ENV__APP_NAME = 'AGENTIC_APP_NAME'


class _EnvScrub:
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k in (ENV__APP_NAME,):
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        os.environ.pop(ENV__APP_NAME, None)
        if self.snapshot.get(ENV__APP_NAME) is not None:
            os.environ[ENV__APP_NAME] = self.snapshot[ENV__APP_NAME]


class test_is_agentic_mode(TestCase):

    def test__agentic_when_app_name_set(self):
        with _EnvScrub(**{ENV__APP_NAME: 'sp-playwright-cli'}):
            assert lambda_handler.is_agentic_mode() is True

    def test__baseline_when_app_name_unset(self):
        with _EnvScrub():
            assert lambda_handler.is_agentic_mode() is False

    def test__baseline_when_app_name_empty(self):
        with _EnvScrub(**{ENV__APP_NAME: ''}):
            assert lambda_handler.is_agentic_mode() is False


class test_module_surface(TestCase):

    def test__exports_handler(self):
        assert hasattr(lambda_handler, 'handler')                                   # Module-level handler — Lambda runtime resolves this string

    def test__class_path_constant_matches_real_class(self):                         # Locks the dotted path; if Fast_API__SP__CLI.module gets renamed this catches it
        assert lambda_handler.SP_CLI_FAST_API_CLASS_PATH == 'sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI.Fast_API__SP__CLI'

    def test__service_label(self):
        assert lambda_handler.SP_CLI_SERVICE_LABEL == 'SP CLI service'
