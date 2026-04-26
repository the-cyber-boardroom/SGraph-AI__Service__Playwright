# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__User__Agent
# Permissive printable-ASCII, capped at 500 chars. Real UAs from the user's
# pasted CF log line (URL-decoded form post Stage 1).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__User__Agent import Safe_Str__CF__User__Agent


WPBOT_UA = 'Mozilla/5.0 (compatible; wpbot/1.4; +https://forms.gle/ajBaxygz9jSR8p8G9)'


class test_Safe_Str__CF__User__Agent(TestCase):

    def test_real_bot_ua_accepted(self):
        assert Safe_Str__CF__User__Agent(WPBOT_UA) == WPBOT_UA

    def test_typical_browser_ua(self):
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        assert Safe_Str__CF__User__Agent(ua) == ua

    def test_empty_allowed(self):
        assert Safe_Str__CF__User__Agent('') == ''

    def test_non_ascii_rejected(self):                                              # Tab / control chars / emoji not allowed
        try:
            Safe_Str__CF__User__Agent('Mozilla\t1.0')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_too_long_rejected(self):
        try:
            Safe_Str__CF__User__Agent('A' * 501)
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
