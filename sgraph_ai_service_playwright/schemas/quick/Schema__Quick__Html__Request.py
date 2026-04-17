# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Quick__Html__Request
#
# Flat, Swagger-friendly request body for POST /quick/html. Deliberately does NOT
# embed Schema__Browser__Config or Schema__Capture__Config — the whole point of
# the /quick/* surface is a short, obvious JSON example in Swagger UI. Sensible
# defaults are applied internally (headless Chromium, no capture sinks, inline
# HTML in response).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.enums.Enum__Wait__State                                  import Enum__Wait__State
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__Selector                    import Safe_Str__Selector
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Timeout_MS                 import Safe_UInt__Timeout_MS


class Schema__Quick__Html__Request(Type_Safe):                                      # Minimal shape: url + optional click + wait + timeout
    url        : Safe_Str__Url
    click      : Safe_Str__Selector    = None                                       # Optional — click this selector before capturing HTML
    wait_until : Enum__Wait__State     = Enum__Wait__State.LOAD
    timeout_ms : Safe_UInt__Timeout_MS = None                                       # Per-step timeout; None -> schema default
