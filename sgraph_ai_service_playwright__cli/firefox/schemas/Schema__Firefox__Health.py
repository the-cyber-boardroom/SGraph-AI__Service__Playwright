# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Health
# Detailed health snapshot returned by GET /firefox/{stack_id}/health.
# Polled by the UI every 10 s. Not the same as Schema__Firefox__Health__Response
# (the legacy wait-loop response); this is the per-component breakdown.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Health__State                import Enum__Health__State
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Health__Detail      import Safe_Str__Health__Detail
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime           import Safe_Str__ISO_Datetime


class Schema__Firefox__Health(Type_Safe):
    container_running : Enum__Health__State  = Enum__Health__State.RED    # is the EC2 instance + Docker container up?
    firefox_process   : Enum__Health__State  = Enum__Health__State.RED    # is the Firefox process inside the container running?
    mitm_proxy        : Enum__Health__State  = Enum__Health__State.RED    # is mitmproxy/mitmweb reachable?
    network           : Enum__Health__State  = Enum__Health__State.RED    # can the instance reach the internet?
    login_page        : Enum__Health__State  = Enum__Health__State.RED    # is the noVNC login page HTTP-reachable?
    overall           : Enum__Health__State  = Enum__Health__State.RED    # worst-of the above
    checked_at        : Safe_Str__ISO_Datetime                            # ISO 8601 UTC timestamp of this check
    detail            : Safe_Str__Health__Detail                          # human-readable note when overall != GREEN
