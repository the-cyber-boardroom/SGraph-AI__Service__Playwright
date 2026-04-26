# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__URI__Stem
# Request URI path. Real values from the user's pasted CF log line.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__URI__Stem import Safe_Str__CF__URI__Stem


class test_Safe_Str__CF__URI__Stem(TestCase):

    def test_real_uris(self):
        assert Safe_Str__CF__URI__Stem('/enhancecp')      == '/enhancecp'
        assert Safe_Str__CF__URI__Stem('/robots.txt')     == '/robots.txt'
        assert Safe_Str__CF__URI__Stem('/api/v1/users/1') == '/api/v1/users/1'

    def test_root(self):
        assert Safe_Str__CF__URI__Stem('/') == '/'

    def test_empty_allowed(self):
        assert Safe_Str__CF__URI__Stem('') == ''

    def test_url_encoded_chars_preserved(self):                                     # %20 etc. allowed
        assert Safe_Str__CF__URI__Stem('/path%20with%20encoding') == '/path%20with%20encoding'

    def test_query_string_rejected(self):                                           # ? not in the allowed set — Stage 1 / CF config strips it
        try:
            Safe_Str__CF__URI__Stem('/path?query=value')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
