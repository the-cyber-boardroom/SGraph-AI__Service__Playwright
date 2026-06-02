# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Open__Response (Φ7)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now

from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Session_Lifetime_MS         import Safe_UInt__Session_Lifetime_MS


class Schema__Session__Open__Response(Type_Safe):                                   # /session/open response
    session_id      : Session_Id                                                    # Caller passes this back in path of /probe, /act, /close
    expires_at_ms   : Timestamp_Now                                                 # Absolute wall-clock (epoch ms) — easier for cross-timezone clients
    expires_in_ms   : Safe_UInt__Session_Lifetime_MS                                # Relative — caller convenience (same number as ttl_ms minus elapsed)
