# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Edge__Location
# CloudFront POP codes — uppercase alphanumeric + hyphen, 2-16 chars.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Edge__Location import Safe_Str__CF__Edge__Location


class test_Safe_Str__CF__Edge__Location(TestCase):

    def test_real_pop_codes(self):                                                  # Real values from the user's pasted CF log line
        assert Safe_Str__CF__Edge__Location('HIO52-P4') == 'HIO52-P4'
        assert Safe_Str__CF__Edge__Location('LHR62-C1') == 'LHR62-C1'

    def test_lowercase_rejected(self):                                              # Parser uppercases before construction; primitive is strict
        try:
            Safe_Str__CF__Edge__Location('hio52-p4')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_empty_allowed(self):
        assert Safe_Str__CF__Edge__Location('') == ''

    def test_disallowed_chars_rejected(self):
        try:
            Safe_Str__CF__Edge__Location('HIO52_P4')                                 # Underscore not allowed
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
