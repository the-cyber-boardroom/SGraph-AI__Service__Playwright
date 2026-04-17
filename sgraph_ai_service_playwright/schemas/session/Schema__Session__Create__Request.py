# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Create__Request (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Lifetime                             import Enum__Session__Lifetime
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Session_Lifetime_MS         import Safe_UInt__Session_Lifetime_MS
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials


class Schema__Session__Create__Request(Type_Safe):                                  # POST /session/create body
    lifetime_hint           : Enum__Session__Lifetime = Enum__Session__Lifetime.EPHEMERAL
    lifetime_ms             : Safe_UInt__Session_Lifetime_MS = 300_000              # 5 min default
    browser_config          : Schema__Browser__Config                                # How to launch browser
    credentials             : Schema__Session__Credentials = None                   # Optional vault-loaded cookies
    capture_config          : Schema__Capture__Config                                # What to capture during session
    trace_id                : Safe_Str__Trace_Id = None                             # Caller may supply; else auto-generated
