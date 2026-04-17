# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Get_Content__Request (v0.1.24)
#
# Navigate + optional click + fetch HTML. Replaces /quick/html.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                          import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Browser__Get_Content__Request(Type_Safe):
    url            : Safe_Str__Url
    click          : Safe_Str__Selector      = None                                 # Optional pre-click
    browser_config : Schema__Browser__Config = None
    wait_until     : Enum__Wait__State       = Enum__Wait__State.LOAD
    timeout_ms     : Safe_UInt__Timeout_MS   = None
