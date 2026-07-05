# ═══════════════════════════════════════════════════════════════════════════════
# Tests — JS__Expression__Allowlist__Loader
#
# The boot-time evaluate policy is env-driven and deny-by-default. No mocks: we set
# real env vars + write a real allowlist file, and scrub in tearDown so the process
# env stays clean for the rest of the suite.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile
from unittest import TestCase

from sg_compute_specs.playwright.core.consts.env_vars                              import (ENV_VAR__JS_ALLOW_ALL     ,
                                                                                          ENV_VAR__JS_ALLOWLIST_FILE)
from sg_compute_specs.playwright.core.service.JS__Expression__Allowlist__Loader    import JS__Expression__Allowlist__Loader


class test_JS__Expression__Allowlist__Loader(TestCase):

    def setUp(self):
        self._snapshot = {k: os.environ.pop(k, None) for k in (ENV_VAR__JS_ALLOW_ALL, ENV_VAR__JS_ALLOWLIST_FILE)}

    def tearDown(self):
        for k, v in self._snapshot.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    # ── deny-all when neither var is set — historical default preserved ──
    def test__unset_is_deny_all(self):
        al = JS__Expression__Allowlist__Loader().load()
        assert al.allow_all             is False
        assert al.allowed_expressions   == []
        assert al.is_enabled()          is False
        assert al.is_allowed('document.title') is False

    # ── allow_all flag accepts the documented truthy spellings ──
    def test__allow_all_truthy_spellings(self):
        for token in ('1', 'true', 'TRUE', 'yes', 'on'):
            os.environ[ENV_VAR__JS_ALLOW_ALL] = token
            assert JS__Expression__Allowlist__Loader().load().allow_all is True, token

    def test__allow_all_falsey_is_deny(self):
        for token in ('0', 'false', 'no', 'off', ''):
            os.environ[ENV_VAR__JS_ALLOW_ALL] = token
            assert JS__Expression__Allowlist__Loader().load().allow_all is False, token

    # ── allowlist file: blanks + '#' comments ignored; exact expressions kept ──
    def test__allowlist_file_parsed(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as fh:
            fh.write("# recon expressions\n() => document.title\n\n  FilterDebug(80)  \n")
            path = fh.name
        try:
            os.environ[ENV_VAR__JS_ALLOWLIST_FILE] = path
            al = JS__Expression__Allowlist__Loader().load()
            assert [str(e) for e in al.allowed_expressions] == ['() => document.title', 'FilterDebug(80)']
            assert al.allow_all              is False                                # curated mode keeps deny-by-default
            assert al.is_enabled()           is True
            assert al.is_allowed('() => document.title') is True
            assert al.is_allowed('alert(1)')             is False
        finally:
            os.remove(path)

    # ── a missing/unreadable file fails CLOSED — never opens scripts, never crashes ──
    def test__missing_file_fails_closed(self):
        os.environ[ENV_VAR__JS_ALLOWLIST_FILE] = '/no/such/allowlist/file.txt'
        al = JS__Expression__Allowlist__Loader().load()
        assert al.allowed_expressions == []
        assert al.is_enabled()        is False
