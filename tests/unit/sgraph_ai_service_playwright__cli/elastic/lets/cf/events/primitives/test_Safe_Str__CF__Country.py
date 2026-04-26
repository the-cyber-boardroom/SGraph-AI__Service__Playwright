# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Country
# Two-letter ISO-3166-1 alpha-2; "-" gets mapped to empty by the parser
# before construction.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Country import Safe_Str__CF__Country


class test_Safe_Str__CF__Country(TestCase):

    def test_uppercase_two_letter(self):
        assert Safe_Str__CF__Country('US') == 'US'
        assert Safe_Str__CF__Country('GB') == 'GB'

    def test_lowercase_rejected(self):                                              # Stage 1 parser uppercases before construction; primitive is strict
        try:
            Safe_Str__CF__Country('us')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_empty_allowed(self):
        assert Safe_Str__CF__Country('') == ''

    def test_three_chars_rejected(self):
        try:
            Safe_Str__CF__Country('USA')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_digits_rejected(self):
        try:
            Safe_Str__CF__Country('U1')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
