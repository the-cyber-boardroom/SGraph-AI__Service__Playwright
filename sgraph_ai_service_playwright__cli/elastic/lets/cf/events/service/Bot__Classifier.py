# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bot__Classifier
# Maps a CloudFront User-Agent string to one of four categories:
#
#   BOT_KNOWN    — UA matches a named-bot pattern (Googlebot, Bingbot, ...)
#   BOT_GENERIC  — UA contains "bot", "spider", "crawler" (etc.) but no
#                  specific named bot
#   HUMAN        — UA matches no bot signature
#   UNKNOWN      — UA is empty
#
# Detection is regex-based and case-insensitive.  The two rule lists are
# class-level constants so subclasses can extend them without re-implementing
# classify().  All regexes are compiled once at module load.
#
# Pure logic — no I/O, no dependencies on other classes.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from typing                                                                         import List, Pattern

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category import Enum__CF__Bot__Category


# ─── Named bots (classify as BOT_KNOWN) ──────────────────────────────────────
# Lowercase patterns against lowercased UA.  Order doesn't matter — first
# match wins, but classify() short-circuits to BOT_KNOWN as soon as any
# match is found.
KNOWN_BOT_PATTERNS: List[Pattern] = [re.compile(p) for p in (
    r'googlebot'             ,                                                       # Google search crawler
    r'bingbot'               ,                                                       # Microsoft Bing
    r'yandexbot'             ,
    r'baiduspider'           ,
    r'duckduckbot'           ,
    r'\bslurp\b'             ,                                                       # Yahoo
    r'facebookexternalhit'   ,
    r'facebot'               ,
    r'applebot'              ,
    r'twitterbot'            ,
    r'linkedinbot'           ,
    r'pinterestbot'          ,
    r'redditbot'             ,
    r'telegrambot'           ,
    r'whatsapp'              ,
    r'discordbot'            ,
    r'semrushbot'            ,
    r'ahrefsbot'             ,
    r'mj12bot'               ,
    r'dotbot'                ,
    r'petalbot'              ,                                                       # Huawei / Petal Search
    r'screaming\s*frog'      ,                                                       # SEO crawler
    r'wpbot'                 ,                                                       # The bot the user observed in real CF logs
    r'\bcurl/'               ,                                                       # curl client (with version, e.g. "curl/7.0")
    r'\bwget/'               ,
    r'\bhttpx/'              ,                                                       # Python httpx
    r'python-requests/'      ,
    r'\bgo-http-client/'     ,
)]


# ─── Generic bot indicators (classify as BOT_GENERIC) ────────────────────────
# Word-boundary regexes — checked only if no KNOWN_BOT_PATTERNS matched.
# Patterns deliberately do NOT include `bot/` — real bot UAs that don't
# carry a known name are rare; the substring "bot" appears in many
# legitimate product names ("NonBotProduct/2.0").  Add a known-bot regex
# above when a new named-bot is spotted in real CF logs.
GENERIC_BOT_PATTERNS: List[Pattern] = [re.compile(p) for p in (
    r'\bspider\b'    ,
    r'\bcrawler\b'   ,
    r'\bscraper?\b'  ,                                                              # scraper / scrape
    r'\bscanner\b'   ,
    r'\bfetcher\b'   ,
)]


class Bot__Classifier(Type_Safe):

    @type_safe
    def classify(self, user_agent: str) -> Enum__CF__Bot__Category:
        if not user_agent:
            return Enum__CF__Bot__Category.UNKNOWN
        ua_lower = user_agent.lower()

        # Step 1: named bots win — most specific
        for pattern in KNOWN_BOT_PATTERNS:
            if pattern.search(ua_lower):
                return Enum__CF__Bot__Category.BOT_KNOWN

        # Step 2: generic indicators (word-bounded regex)
        for pattern in GENERIC_BOT_PATTERNS:
            if pattern.search(ua_lower):
                return Enum__CF__Bot__Category.BOT_GENERIC

        # Step 3: nothing matched — call it human
        return Enum__CF__Bot__Category.HUMAN
