# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Get_Url__Request (v0.1.24)
#
# Navigate + optional click + report final URL (post-redirects / post-click).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                          import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Browser__Get_Url__Request(Type_Safe):
    url            : Safe_Str__Url
    click          : Safe_Str__Selector      = None                                 # Optional pre-click
    browser_config : Schema__Browser__Config = None
    wait_until     : Enum__Wait__State       = Enum__Wait__State.LOAD
    timeout_ms     : Safe_UInt__Timeout_MS   = None
