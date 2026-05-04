# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Schema__Vnc__Health
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.vnc.enums.Enum__Vnc__Stack__State                             import Enum__Vnc__Stack__State
from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Stack__Name                     import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Health(Type_Safe):
    stack_name   : Safe_Str__Vnc__Stack__Name
    state        : Enum__Vnc__Stack__State = Enum__Vnc__Stack__State.UNKNOWN
    nginx_ok     : bool                    = False
    mitmweb_ok   : bool                    = False
    flow_count   : int                     = -1
    error        : Safe_Str__Text
