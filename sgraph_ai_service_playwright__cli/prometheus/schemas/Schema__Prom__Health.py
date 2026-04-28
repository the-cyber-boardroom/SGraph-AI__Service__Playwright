# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Prom__Health
# Health snapshot returned by `sp prom health <name>` and the matching FastAPI
# route. Captures Prometheus reachability + scrape-target counts. Mirrors
# Schema__OS__Health but uses Prometheus' vocabulary:
#   /-/healthy   → prometheus_ok
#   /api/v1/targets → targets_total / targets_up
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name


class Schema__Prom__Health(Type_Safe):
    stack_name      : Safe_Str__Prom__Stack__Name
    state           : Enum__Prom__Stack__State = Enum__Prom__Stack__State.UNKNOWN
    prometheus_ok   : bool                     = False                              # True iff /-/healthy responds 200
    targets_total   : int                      = -1                                 # -1 ⇒ unreachable; 0 is a valid 'no targets configured'
    targets_up      : int                      = -1                                 # -1 ⇒ unreachable; count of active scrape targets in 'up' health
    error           : Safe_Str__Text                                                # Set when any probe failed; empty otherwise
