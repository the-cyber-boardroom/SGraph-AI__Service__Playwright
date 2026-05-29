# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Root_Path__Resolver
#
# Resolution precedence: X-Forwarded-Prefix header → SG_PLAYWRIGHT__ROOT_PATH env
# → /pw default. The '/' env sentinel forces standalone (no prefix). All results
# normalised (no trailing slash; '' = no prefix).
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                          import TestCase

from sg_compute_specs.playwright.core.consts.env_vars                                     import ENV_VAR__ROOT_PATH
from sg_compute_specs.playwright.core.service.Root_Path__Resolver                         import (Root_Path__Resolver,
                                                                                                 DEFAULT_ROOT_PATH    )


class _FakeRequest:                                                                    # only .headers.get is exercised
    def __init__(self, headers: dict = None):
        self.headers = headers or {}


class test_Root_Path__Resolver(TestCase):

    def setup_method(self, method):
        self._saved = os.environ.pop(ENV_VAR__ROOT_PATH, None)

    def teardown_method(self, method):
        os.environ.pop(ENV_VAR__ROOT_PATH, None)
        if self._saved is not None:
            os.environ[ENV_VAR__ROOT_PATH] = self._saved

    # ── default ────────────────────────────────────────────────────────────────

    def test__default_is_pw_when_unset_and_no_request(self):
        assert Root_Path__Resolver().resolve() == DEFAULT_ROOT_PATH
        assert DEFAULT_ROOT_PATH == '/pw'

    def test__default_is_pw_when_request_has_no_header(self):
        assert Root_Path__Resolver().resolve(_FakeRequest()) == '/pw'

    # ── env override ─────────────────────────────────────────────────────────────

    def test__env_overrides_default(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/custom'
        assert Root_Path__Resolver().resolve(_FakeRequest()) == '/custom'

    def test__env_trailing_slash_stripped(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/custom/'
        assert Root_Path__Resolver().resolve() == '/custom'

    def test__slash_sentinel_means_no_prefix(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/'
        assert Root_Path__Resolver().resolve(_FakeRequest()) == ''

    # ── header precedence (highest) ──────────────────────────────────────────────

    def test__header_wins_over_env(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/pw'
        req = _FakeRequest({'x-forwarded-prefix': '/automation'})
        assert Root_Path__Resolver().resolve(req) == '/automation'

    def test__header_wins_over_default(self):
        req = _FakeRequest({'x-forwarded-prefix': '/pw'})
        assert Root_Path__Resolver().resolve(req) == '/pw'

    def test__header_trailing_slash_stripped(self):
        req = _FakeRequest({'x-forwarded-prefix': '/pw/'})
        assert Root_Path__Resolver().resolve(req) == '/pw'

    def test__empty_header_falls_through_to_env(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/custom'
        req = _FakeRequest({'x-forwarded-prefix': ''})
        assert Root_Path__Resolver().resolve(req) == '/custom'
