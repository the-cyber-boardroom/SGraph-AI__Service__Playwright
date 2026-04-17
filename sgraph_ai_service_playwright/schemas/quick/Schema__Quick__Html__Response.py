# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Quick__Html__Response
#
# Flat response for POST /quick/html. `url` is what the caller asked for;
# `final_url` is the browser's post-navigate (and post-click) URL — usually the
# same, but differs on redirects or client-side nav.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds               import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.primitives.text.Safe_Str__Page__Content                  import Safe_Str__Page__Content


class Schema__Quick__Html__Response(Type_Safe):
    url         : Safe_Str__Url                                                     # What the caller asked for
    final_url   : Safe_Str__Url                                                     # Browser's current URL after navigate + optional click
    html        : Safe_Str__Page__Content                                           # Full page HTML (page.content()) — 10 MB cap; real pages exceed the 64 KB default of Safe_Str__Text__Dangerous
    duration_ms : Safe_UInt__Milliseconds
