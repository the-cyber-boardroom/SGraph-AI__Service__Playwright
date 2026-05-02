# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Schema__Podman__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.podman.primitives.Safe_Str__Podman__Stack__Name               import Safe_Str__Podman__Stack__Name


class Schema__Podman__Delete__Response(Type_Safe):
    stack_name   : Safe_Str__Podman__Stack__Name
    deleted      : bool = False
    message      : Safe_Str__Text
    elapsed_ms   : int  = 0
