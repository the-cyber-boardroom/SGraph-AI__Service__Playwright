# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Navigate__Request (v0.1.24)
#
# Flat, Swagger-friendly body for POST /browser/navigate. One-shot: fresh
# Chromium per call, run the navigate, tear down. Optional browser_config
# controls engine, headless, viewport, user-agent, locale, timezone.
# Proxy is boot-time infrastructure (SG_PLAYWRIGHT__DEFAULT_PROXY_URL), not
# a per-request API parameter.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                          import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.browser.Schema__Viewport                                 import Schema__Viewport
from sg_compute_specs.playwright.core.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Browser__Navigate__Request(Type_Safe):
    url            : Safe_Str__Url
    viewport       : Schema__Viewport        = None                                 # Shorthand for browser_config.viewport — avoids nesting
    browser_config : Schema__Browser__Config = None                                 # Optional — launch defaults applied when omitted
    wait_until     : Enum__Wait__State       = Enum__Wait__State.LOAD
    timeout_ms     : Safe_UInt__Timeout_MS   = None
