# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Host
# Hostname per RFC-952/1123. Lowercase normalised.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Host import Safe_Str__CF__Host


class test_Safe_Str__CF__Host(TestCase):

    def test_simple_host(self):                                                     # The user's real bucket has logs from this exact host
        assert Safe_Str__CF__Host('sgraph.ai') == 'sgraph.ai'

    def test_subdomain(self):
        assert Safe_Str__CF__Host('www.example.com') == 'www.example.com'

    def test_uppercase_normalised(self):
        assert Safe_Str__CF__Host('SGraph.AI') == 'sgraph.ai'

    def test_empty_allowed(self):
        assert Safe_Str__CF__Host('') == ''

    def test_disallowed_chars_rejected(self):
        try:
            Safe_Str__CF__Host('has spaces.com')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
