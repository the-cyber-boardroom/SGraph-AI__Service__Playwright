# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Content__Type
# MIME type with optional parameters. Lowercase normalised.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Content__Type import Safe_Str__CF__Content__Type


class test_Safe_Str__CF__Content__Type(TestCase):

    def test_simple_mime(self):
        assert Safe_Str__CF__Content__Type('text/html')        == 'text/html'
        assert Safe_Str__CF__Content__Type('application/xml')  == 'application/xml'
        assert Safe_Str__CF__Content__Type('application/json') == 'application/json'

    def test_with_charset_parameter(self):
        assert Safe_Str__CF__Content__Type('text/html; charset=utf-8') == 'text/html; charset=utf-8'

    def test_uppercase_normalised(self):
        assert Safe_Str__CF__Content__Type('Application/JSON') == 'application/json'

    def test_empty_allowed(self):                                                   # CF emits "-" when no Content-Type; parser maps to empty
        assert Safe_Str__CF__Content__Type('') == ''
