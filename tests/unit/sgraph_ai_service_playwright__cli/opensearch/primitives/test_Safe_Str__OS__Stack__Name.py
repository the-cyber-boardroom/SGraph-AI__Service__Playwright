# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__OS__Stack__Name
# Mirrors the Safe_Str__Elastic__Stack__Name test surface; both regexes are
# identical so the same edge cases apply.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Stack__Name      import Safe_Str__OS__Stack__Name


class test_Safe_Str__OS__Stack__Name(TestCase):

    def test__valid_names(self):
        for name in ('opensearch-quiet-fermi', 'os-prod', 'aaa', 'a-1-b-2-c'):
            assert str(Safe_Str__OS__Stack__Name(name)) == name

    def test__lowercases(self):                                                      # to_lower_case=True
        assert str(Safe_Str__OS__Stack__Name('OpenSearch-PROD')) == 'opensearch-prod'

    def test__trims_whitespace(self):
        assert str(Safe_Str__OS__Stack__Name('  os-foo  ')) == 'os-foo'

    def test__rejects_starting_with_digit(self):
        with self.assertRaises(ValueError):
            Safe_Str__OS__Stack__Name('1-bad-start')

    def test__rejects_underscore(self):                                              # Regex allows letters/digits/hyphens only
        with self.assertRaises(ValueError):
            Safe_Str__OS__Stack__Name('os_bad')

    def test__rejects_uppercase_after_lowercasing_changes_value(self):               # to_lower_case applies before regex; pure-uppercase becomes valid lowercase
        assert str(Safe_Str__OS__Stack__Name('FOO-BAR')) == 'foo-bar'                # No raise — lowercase happens first

    def test__rejects_too_short(self):                                               # Min 2 chars (letter + 1 more)
        with self.assertRaises(ValueError):
            Safe_Str__OS__Stack__Name('a')

    def test__rejects_too_long(self):
        with self.assertRaises(ValueError):
            Safe_Str__OS__Stack__Name('a' + 'b' * 63)                                # 64 chars total, max is 63

    def test__empty_allowed(self):                                                   # allow_empty=True so service can auto-init and reject empty later
        assert str(Safe_Str__OS__Stack__Name('')) == ''

    def test__regex_matches_elastic_shape(self):                                     # OS and elastic stack names share the same regex by design
        from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
        assert Safe_Str__OS__Stack__Name.regex.pattern == Safe_Str__Elastic__Stack__Name.regex.pattern
