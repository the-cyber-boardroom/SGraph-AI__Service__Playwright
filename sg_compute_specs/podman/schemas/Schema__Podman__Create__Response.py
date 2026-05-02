# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Schema__Podman__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.podman.schemas.Schema__Podman__Info                           import Schema__Podman__Info


class Schema__Podman__Create__Response(Type_Safe):
    stack_info   : Schema__Podman__Info
    message      : Safe_Str__Text
    elapsed_ms   : int = 0
