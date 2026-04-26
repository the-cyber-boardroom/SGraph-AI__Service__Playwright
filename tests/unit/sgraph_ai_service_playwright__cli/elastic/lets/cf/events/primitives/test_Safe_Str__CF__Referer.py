# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Referer
# Printable ASCII, query-stripped by Stage 1 before construction.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Referer import Safe_Str__CF__Referer


class test_Safe_Str__CF__Referer(TestCase):

    def test_url_with_path(self):
        assert Safe_Str__CF__Referer('https://example.com/page') == 'https://example.com/page'

    def test_root_url(self):
        assert Safe_Str__CF__Referer('https://google.com/') == 'https://google.com/'

    def test_empty_allowed(self):                                                   # CF emits "-" for missing referer; parser maps to empty
        assert Safe_Str__CF__Referer('') == ''
