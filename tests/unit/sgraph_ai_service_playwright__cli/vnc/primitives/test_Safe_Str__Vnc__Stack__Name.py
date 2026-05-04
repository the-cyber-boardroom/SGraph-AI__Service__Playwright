# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__Vnc__Stack__Name
# Locks the regex + parity with elastic / opensearch / prometheus.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Stack__Name    import Safe_Str__Vnc__Stack__Name


class test_Safe_Str__Vnc__Stack__Name(TestCase):

    def test__valid_names(self):
        for ok in ('vnc-quiet-fermi', 'vnc-prod', 'a1', 'browser-viewer-debug-1'):
            assert str(Safe_Str__Vnc__Stack__Name(ok)) == ok

    def test__lowercases(self):
        assert str(Safe_Str__Vnc__Stack__Name('VNC-Prod')) == 'vnc-prod'

    def test__rejects_start_with_digit(self):
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Stack__Name('1bad')

    def test__rejects_underscore(self):
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Stack__Name('vnc_prod')

    def test__empty_allowed(self):
        assert str(Safe_Str__Vnc__Stack__Name('')) == ''

    def test__regex_parity_with_elastic_and_opensearch_and_prom(self):              # All sister sections share the same naming shape
        from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
        from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Stack__Name   import Safe_Str__OS__Stack__Name
        from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name
        assert Safe_Str__Vnc__Stack__Name.regex.pattern == Safe_Str__Elastic__Stack__Name.regex.pattern
        assert Safe_Str__Vnc__Stack__Name.regex.pattern == Safe_Str__OS__Stack__Name.regex.pattern
        assert Safe_Str__Vnc__Stack__Name.regex.pattern == Safe_Str__Prom__Stack__Name.regex.pattern
