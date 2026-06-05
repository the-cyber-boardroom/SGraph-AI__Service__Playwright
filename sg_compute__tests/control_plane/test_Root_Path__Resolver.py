# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute.control_plane.Root_Path__Resolver
#
# Resolution precedence: X-Forwarded-Prefix header → SG_COMPUTE__ROOT_PATH env →
# /host default. The '/' env sentinel forces standalone (no prefix). All
# results normalised (no trailing slash; '' = no prefix).
#
# Mirrors tests/unit/service/test_Root_Path__Resolver.py (the sg-playwright
# resolver tests) — keeping them in lock-step prevents drift the way
# Page__Factory's discipline test does for new_context() callers.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from sg_compute.control_plane.Root_Path__Resolver import (
    Root_Path__Resolver,
    DEFAULT_ROOT_PATH,
    ENV_VAR__ROOT_PATH,
    HEADER__FORWARDED_PREFIX,
    PROXY_PREFIX,
    SENTINEL__NO_PREFIX,
)


class _FakeRequest:                                                                # only .headers.get is exercised
    def __init__(self, headers: dict = None):
        self.headers = headers or {}


class test_Root_Path__Resolver(TestCase):

    def setUp(self):
        self._saved = os.environ.pop(ENV_VAR__ROOT_PATH, None)

    def tearDown(self):
        os.environ.pop(ENV_VAR__ROOT_PATH, None)
        if self._saved is not None:
            os.environ[ENV_VAR__ROOT_PATH] = self._saved

    # ── default ─────────────────────────────────────────────────────────────────

    def test__default_is_empty_when_unset_and_no_request(self):                       # No positive signal → no root_path; matches direct-access / test-client behaviour. Proxy supplies '/host' via the header.
        assert Root_Path__Resolver().resolve() == ''
        assert DEFAULT_ROOT_PATH == ''
        assert PROXY_PREFIX == '/host'                                                # documented convention, not auto-applied

    def test__default_is_empty_when_request_has_no_header(self):
        assert Root_Path__Resolver().resolve(_FakeRequest()) == ''

    # ── env override ────────────────────────────────────────────────────────────

    def test__env_overrides_default(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/custom'
        assert Root_Path__Resolver().resolve(_FakeRequest()) == '/custom'

    def test__env_trailing_slash_stripped(self):
        os.environ[ENV_VAR__ROOT_PATH] = '/custom/'
        assert Root_Path__Resolver().resolve() == '/custom'

    def test__env_empty_string_falls_through_to_default(self):                       # empty == unset for env semantics
        os.environ[ENV_VAR__ROOT_PATH] = ''
        assert Root_Path__Resolver().resolve() == ''

    def test__env_slash_sentinel_means_no_prefix(self):                              # explicit standalone signal
        os.environ[ENV_VAR__ROOT_PATH] = SENTINEL__NO_PREFIX
        assert Root_Path__Resolver().resolve() == ''

    # ── header beats env ────────────────────────────────────────────────────────

    def test__forwarded_prefix_header_beats_env_var(self):                            # per-request header wins so the same image works behind any proxy
        os.environ[ENV_VAR__ROOT_PATH] = '/env-set'
        req = _FakeRequest({HEADER__FORWARDED_PREFIX: '/from-proxy'})
        assert Root_Path__Resolver().resolve(req) == '/from-proxy'

    def test__forwarded_prefix_header_trailing_slash_stripped(self):
        req = _FakeRequest({HEADER__FORWARDED_PREFIX: '/host/'})
        assert Root_Path__Resolver().resolve(req) == '/host'

    def test__empty_forwarded_prefix_header_falls_through_to_env_then_default(self):  # an empty header value shouldn't pin root_path — fall through to env (here unset) then to default ''
        req = _FakeRequest({HEADER__FORWARDED_PREFIX: ''})
        assert Root_Path__Resolver().resolve(req) == ''

    # ── proxy-case integration: header carries the /host prefix ──────────────────

    def test__proxy_supplied_host_prefix_is_returned_verbatim(self):                  # The actual production case: vault Fast_API__Reverse_Proxy sends X-Forwarded-Prefix: /host
        req = _FakeRequest({HEADER__FORWARDED_PREFIX: PROXY_PREFIX})
        assert Root_Path__Resolver().resolve(req) == PROXY_PREFIX
