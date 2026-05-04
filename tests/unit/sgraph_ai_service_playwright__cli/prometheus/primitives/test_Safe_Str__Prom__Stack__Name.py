# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__Prom__Stack__Name
# Mirrors the elastic + opensearch versions; same regex by design.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name


class test_Safe_Str__Prom__Stack__Name(TestCase):

    def test__valid_names(self):
        for name in ('prom-quiet-fermi', 'prometheus-prod', 'pp1'):
            assert str(Safe_Str__Prom__Stack__Name(name)) == name

    def test__lowercases(self):
        assert str(Safe_Str__Prom__Stack__Name('Prom-PROD')) == 'prom-prod'

    def test__rejects_starting_with_digit(self):
        with self.assertRaises(ValueError):
            Safe_Str__Prom__Stack__Name('1-bad')

    def test__rejects_underscore(self):
        with self.assertRaises(ValueError):
            Safe_Str__Prom__Stack__Name('prom_bad')

    def test__empty_allowed(self):
        assert str(Safe_Str__Prom__Stack__Name('')) == ''

    def test__regex_matches_opensearch_and_elastic(self):                            # Sister sections share the regex by design
        from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
        from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Stack__Name   import Safe_Str__OS__Stack__Name
        assert Safe_Str__Prom__Stack__Name.regex.pattern == Safe_Str__Elastic__Stack__Name.regex.pattern
        assert Safe_Str__Prom__Stack__Name.regex.pattern == Safe_Str__OS__Stack__Name      .regex.pattern
