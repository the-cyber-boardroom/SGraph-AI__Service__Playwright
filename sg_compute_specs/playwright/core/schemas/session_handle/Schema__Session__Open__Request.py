# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Open__Request (Φ7 — opt-in stateful)
#
# Body for POST /session/open. Launches Chromium + creates a page + attaches
# the listener buffer, then holds them in Session__Registry under a
# caller-opaque session_id for subsequent /probe and /act calls.
#
# ttl_ms is capped at deployment.max_session_lifetime_ms (returned in the
# capabilities endpoint); requests beyond that are rejected at validation.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Session_Lifetime_MS         import Safe_UInt__Session_Lifetime_MS
from sg_compute_specs.playwright.core.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials


class Schema__Session__Open__Request(Type_Safe):                                    # POST /session/open body
    browser_config : Schema__Browser__Config       = None                           # Optional — defaults to headless Chromium
    credentials    : Schema__Session__Credentials  = None                           # Applied once at open; subsequent /act + /probe inherit
    ttl_ms         : Safe_UInt__Session_Lifetime_MS = 300_000                       # 5 minutes default; capped at capabilities.max_session_lifetime_ms
