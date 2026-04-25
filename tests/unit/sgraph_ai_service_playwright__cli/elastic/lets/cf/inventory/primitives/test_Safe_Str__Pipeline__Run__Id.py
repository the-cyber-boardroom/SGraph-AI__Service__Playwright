# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__Pipeline__Run__Id
# The primitive is intentionally permissive; the precise format ({iso8601}-
# {source}-{verb}-{shortsha}) is enforced by the service-side generator.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id


class test_Safe_Str__Pipeline__Run__Id(TestCase):

    def test_canonical_format(self):                                                # The shape the generator will produce
        v = Safe_Str__Pipeline__Run__Id('20260425T103042Z-cf-realtime-load-a3f2')
        assert v == '20260425T103042Z-cf-realtime-load-a3f2'

    def test_simple_test_id(self):                                                  # Tests can pass any short ASCII id without fighting the regex
        assert Safe_Str__Pipeline__Run__Id('test-run-1') == 'test-run-1'

    def test_empty_allowed_for_auto_generate(self):
        assert Safe_Str__Pipeline__Run__Id('') == ''

    def test_disallowed_char_rejected(self):                                        # No spaces, no slashes, no dots
        try:
            Safe_Str__Pipeline__Run__Id('has spaces')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
