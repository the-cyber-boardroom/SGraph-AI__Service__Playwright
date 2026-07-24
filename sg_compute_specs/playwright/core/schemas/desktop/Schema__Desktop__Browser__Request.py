# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Desktop__Browser__Request
# Body for POST /desktop/browser (vnc display mode only): open a long-lived
# HEADED browser on the container's X display (:99) so it is visible/drivable in
# noVNC. Internally a session (Session__Registry) — the response's session_id
# works with every /session/{id}/* endpoint (act/probe/close), which is how
# automation and the human share the same browser.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                                 import Enum__Browser__Name
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Session_Lifetime_MS         import Safe_UInt__Session_Lifetime_MS
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive


class Schema__Desktop__Browser__Request(Type_Safe):                                # POST /desktop/browser body
    engine    : Enum__Browser__Name             = Enum__Browser__Name.CHROMIUM     # chromium | firefox (both ship in the Playwright base image)
    start_url : Safe_Str__Url__Permissive       = None                             # navigated to after launch; None → blank page
    ttl_ms    : Safe_UInt__Session_Lifetime_MS  = 3_600_000                        # desktop sessions default long (1h); capped at capabilities.max_session_lifetime_ms
