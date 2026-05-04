# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Schema__Docker__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.docker.schemas.Schema__Docker__Info                           import Schema__Docker__Info


class Schema__Docker__Create__Response(Type_Safe):
    stack_info   : Schema__Docker__Info
    message      : Safe_Str__Text
    elapsed_ms   : int = 0
