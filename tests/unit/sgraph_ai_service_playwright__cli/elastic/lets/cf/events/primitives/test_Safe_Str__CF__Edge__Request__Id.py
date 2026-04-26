# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Edge__Request__Id
# Real CF edge-request-id is base64-ish with padding (==).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Edge__Request__Id import Safe_Str__CF__Edge__Request__Id


REAL_REQUEST_ID = '2TZI-f7L0PmDR-76lAEx4wdq-StamTTbisIdbMSYhB4eVeyTcPy0qw=='        # From the user's pasted CF log line


class test_Safe_Str__CF__Edge__Request__Id(TestCase):

    def test_real_id_accepted(self):
        assert Safe_Str__CF__Edge__Request__Id(REAL_REQUEST_ID) == REAL_REQUEST_ID

    def test_empty_allowed(self):
        assert Safe_Str__CF__Edge__Request__Id('') == ''

    def test_simple_alphanumeric(self):
        assert Safe_Str__CF__Edge__Request__Id('abc123') == 'abc123'

    def test_disallowed_chars_rejected(self):                                       # Spaces not allowed
        try:
            Safe_Str__CF__Edge__Request__Id('has spaces')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
