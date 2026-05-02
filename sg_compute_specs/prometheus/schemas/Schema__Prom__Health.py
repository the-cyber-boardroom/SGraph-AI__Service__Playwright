# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Schema__Prom__Health
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.prometheus.enums.Enum__Prom__Stack__State                     import Enum__Prom__Stack__State
from sg_compute_specs.prometheus.primitives.Safe_Str__Prom__Stack__Name             import Safe_Str__Prom__Stack__Name


class Schema__Prom__Health(Type_Safe):
    stack_name    : Safe_Str__Prom__Stack__Name
    state         : Enum__Prom__Stack__State = Enum__Prom__Stack__State.UNKNOWN
    prometheus_ok : bool                     = False
    targets_total : int                      = -1                                   # -1 ⇒ unreachable
    targets_up    : int                      = -1
    error         : Safe_Str__Text
