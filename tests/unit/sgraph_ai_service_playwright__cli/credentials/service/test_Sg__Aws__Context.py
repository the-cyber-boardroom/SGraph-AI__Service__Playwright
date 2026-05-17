# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Sg__Aws__Context (Phase D)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context


class test_Sg__Aws__Context(TestCase):

    def test__default_has_no_role(self):
        ctx = Sg__Aws__Context()
        assert ctx.has_role() is False

    def test__set_role_sets_current_role(self):
        ctx = Sg__Aws__Context()
        ctx.set_role('admin')
        assert ctx.has_role() is True
        assert str(ctx.current_role) == 'admin'

    def test__clear_role_clears_current_role(self):
        ctx = Sg__Aws__Context()
        ctx.set_role('admin')
        ctx.clear_role()
        assert ctx.has_role() is False
        assert str(ctx.current_role) == ''

    def test__set_role_returns_self(self):
        ctx    = Sg__Aws__Context()
        result = ctx.set_role('dev')
        assert result is ctx

    def test__clear_role_returns_self(self):
        ctx    = Sg__Aws__Context()
        result = ctx.clear_role()
        assert result is ctx

    def test__set_role_normalises_via_safe_str(self):
        ctx = Sg__Aws__Context()
        ctx.set_role('admin')                               # lowercase role name passes through unchanged
        assert str(ctx.current_role) == 'admin'

    def test__multiple_set_role_calls_overwrite(self):
        ctx = Sg__Aws__Context()
        ctx.set_role('admin')
        ctx.set_role('dev')
        assert str(ctx.current_role) == 'dev'
