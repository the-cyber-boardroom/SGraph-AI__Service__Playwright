# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Screenshot__Request (v0.1.24)
#
# Navigate + optional click + screenshot. Route returns raw image/png with
# X-*-Ms timing headers (body is raw PNG bytes — no room for JSON).
#
# viewport is a top-level shorthand for browser_config.viewport — callers
# can pass {"url":"...", "full_page":true, "viewport":{"width":1280,"height":800}}
# without wrapping in browser_config.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                          import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.browser.Schema__Viewport                                 import Schema__Viewport
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Browser__Screenshot__Request(Type_Safe):
    url            : Safe_Str__Url
    selector       : Safe_Str__Selector      = None                                 # Element-only screenshot if set; else viewport
    click          : Safe_Str__Selector      = None                                 # Optional pre-click before capturing
    full_page      : bool                    = False                                # Scroll-to-render full page (ignored if selector set)
    viewport       : Schema__Viewport        = None                                 # Shorthand for browser_config.viewport — avoids nesting
    browser_config : Schema__Browser__Config = None
    wait_until     : Enum__Wait__State       = Enum__Wait__State.LOAD
    timeout_ms     : Safe_UInt__Timeout_MS   = None
