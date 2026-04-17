# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Navigate__Request (v0.1.24)
#
# Flat, Swagger-friendly body for POST /browser/navigate. One-shot: fresh
# Chromium per call, run the navigate, tear down. Optional browser_config
# lets callers pass proxy settings (incl. Schema__Proxy__Auth__Basic) on a
# per-request basis — stateless by design.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                          import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Browser__Navigate__Request(Type_Safe):
    url            : Safe_Str__Url
    browser_config : Schema__Browser__Config = None                                 # Optional — launch defaults applied when omitted
    wait_until     : Enum__Wait__State       = Enum__Wait__State.LOAD
    timeout_ms     : Safe_UInt__Timeout_MS   = None
