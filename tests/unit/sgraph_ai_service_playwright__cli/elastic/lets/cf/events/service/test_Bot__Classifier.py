# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Bot__Classifier
# Pins the four categories.  Real bot UAs from the user's CF log + canned
# human / generic / unknown samples.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category import Enum__CF__Bot__Category
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier      import Bot__Classifier


WPBOT_UA       = 'Mozilla/5.0 (compatible; wpbot/1.4; +https://forms.gle/foo)'      # Real bot from user's CF log
GOOGLEBOT_UA   = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
BINGBOT_UA     = 'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)'
CURL_UA        = 'curl/7.85.0'
CHROME_UA      = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36'
SAFARI_UA      = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'
GENERIC_BOT_UA = 'Mozilla/5.0 (compatible; Crawler/1.0; +https://example.com)'      # No specific named bot, but matches the generic "crawler" indicator (word-bounded)
NO_BOT_HINT_UA = 'Mozilla/5.0 SomethingNonBot/2.0'                                  # Should classify as HUMAN — "Bot" inside a word does NOT trigger the classifier


class test_Bot__Classifier(TestCase):

    def test_empty_returns_unknown(self):
        assert Bot__Classifier().classify('') == Enum__CF__Bot__Category.UNKNOWN

    def test_known_bots(self):                                                      # The named bots we explicitly recognise
        c = Bot__Classifier()
        assert c.classify(WPBOT_UA)     == Enum__CF__Bot__Category.BOT_KNOWN
        assert c.classify(GOOGLEBOT_UA) == Enum__CF__Bot__Category.BOT_KNOWN
        assert c.classify(BINGBOT_UA)   == Enum__CF__Bot__Category.BOT_KNOWN
        assert c.classify(CURL_UA)      == Enum__CF__Bot__Category.BOT_KNOWN

    def test_generic_bot_indicator(self):                                           # "CustomScannerBot/1.0" — no specific named bot but matches "scanner" / "bot/"
        assert Bot__Classifier().classify(GENERIC_BOT_UA) == Enum__CF__Bot__Category.BOT_GENERIC

    def test_known_overrides_generic(self):                                         # When a UA could match BOTH known + generic, known wins
        # wpbot is in KNOWN_BOT_PATTERNS AND also contains "bot" generically
        assert Bot__Classifier().classify(WPBOT_UA) == Enum__CF__Bot__Category.BOT_KNOWN

    def test_human_uas(self):                                                       # Real-browser UAs with no bot hint at all
        c = Bot__Classifier()
        assert c.classify(CHROME_UA)      == Enum__CF__Bot__Category.HUMAN
        assert c.classify(SAFARI_UA)      == Enum__CF__Bot__Category.HUMAN
        assert c.classify(NO_BOT_HINT_UA) == Enum__CF__Bot__Category.HUMAN

    def test_case_insensitive(self):                                                # UAs in the wild come in various cases
        c = Bot__Classifier()
        assert c.classify('GOOGLEBOT/2.1') == Enum__CF__Bot__Category.BOT_KNOWN
        assert c.classify('Googlebot/2.1') == Enum__CF__Bot__Category.BOT_KNOWN
