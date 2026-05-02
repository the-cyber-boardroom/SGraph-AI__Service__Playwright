# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info


class Schema__Node__Create__Response(Type_Safe):
    node   : Schema__Node__Info
    status : str = ''
