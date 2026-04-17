# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Screenshot__Request (v0.1.24)
#
# Navigate + optional click + screenshot. Route returns raw image/png with
# X-*-Ms timing headers (body is raw PNG bytes — no room for JSON).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                          import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Browser__Screenshot__Request(Type_Safe):
    url            : Safe_Str__Url
    selector       : Safe_Str__Selector      = None                                 # Element-only screenshot if set; else viewport
    click          : Safe_Str__Selector      = None                                 # Optional pre-click before capturing
    full_page      : bool                    = False                                # Scroll-to-render full page (ignored if selector set)
    browser_config : Schema__Browser__Config = None
    wait_until     : Enum__Wait__State       = Enum__Wait__State.LOAD
    timeout_ms     : Safe_UInt__Timeout_MS   = None
