# ═══════════════════════════════════════════════════════════════════════════════
# Tests — JS__Expression__Allowlist
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__JS__Expression    import Safe_Str__JS__Expression
from sgraph_ai_service_playwright.service.JS__Expression__Allowlist                       import JS__Expression__Allowlist


class test_JS__Expression__Allowlist(TestCase):

    def test__default_is_deny_all(self):
        al = JS__Expression__Allowlist()
        assert al.allowed_expressions         == []
        assert al.is_allowed('document.title') is False
        assert al.is_allowed('1+1'           ) is False

    def test__exact_match_is_allowed(self):
        al = JS__Expression__Allowlist(allowed_expressions=['document.title'])
        assert al.is_allowed('document.title') is True

    def test__partial_match_is_rejected(self):                                      # Exact-match only — substring must not pass
        al = JS__Expression__Allowlist(allowed_expressions=['document.title'])
        assert al.is_allowed('document.title;alert(1)') is False
        assert al.is_allowed('document'                ) is False

    def test__accepts_safe_str_argument(self):                                      # Callers pass a Safe_Str__JS__Expression, not a raw str
        al = JS__Expression__Allowlist(allowed_expressions=['document.title'])
        expr = Safe_Str__JS__Expression('document.title')
        assert al.is_allowed(expr) is True
