# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Local_Claude__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Info import Schema__Local_Claude__Info


class Schema__Local_Claude__Create__Response(Type_Safe):
    stack_info  : Schema__Local_Claude__Info = None
    message     : str = ''
    elapsed_ms  : int = 0
