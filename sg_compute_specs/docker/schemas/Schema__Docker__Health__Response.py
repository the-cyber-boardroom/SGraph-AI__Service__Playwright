# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Schema__Docker__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.docker.enums.Enum__Docker__Stack__State                       import Enum__Docker__Stack__State
from sg_compute_specs.docker.primitives.Safe_Str__Docker__Stack__Name               import Safe_Str__Docker__Stack__Name


class Schema__Docker__Health__Response(Type_Safe):
    stack_name    : Safe_Str__Docker__Stack__Name
    state         : Enum__Docker__Stack__State = Enum__Docker__Stack__State.UNKNOWN
    healthy       : bool = False
    ssm_reachable : bool = False
    docker_ok     : bool = False
    docker_version: Safe_Str__Text
    message       : Safe_Str__Text
    elapsed_ms    : int  = 0
