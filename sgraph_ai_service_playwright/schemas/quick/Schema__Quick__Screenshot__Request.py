# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Quick__Screenshot__Request
#
# Flat, Swagger-friendly request body for POST /quick/screenshot. Response is
# raw PNG bytes (image/png) rather than JSON — Swagger UI renders a "Download
# file" button. Sensible defaults applied internally (headless Chromium, INLINE
# capture sink so we can pull the PNG bytes back from the artefact).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Quick__Screenshot__Request(Type_Safe):                                # Minimal shape: url + optional click/selector/full_page
    url        : Safe_Str__Url
    selector   : Safe_Str__Selector    = None                                       # Element-only screenshot if set; else viewport
    click      : Safe_Str__Selector    = None                                       # Optional — click this selector before capturing
    full_page  : bool                  = False                                      # True -> scroll-to-render full page (ignored if selector set)
    wait_until : Enum__Wait__State     = Enum__Wait__State.LOAD
    timeout_ms : Safe_UInt__Timeout_MS = None
