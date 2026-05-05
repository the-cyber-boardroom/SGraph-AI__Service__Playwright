# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Credentials__Response
# Response for PUT /api/specs/firefox/{node_id}/credentials
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Schema__Firefox__Credentials__Response(Type_Safe):
    node_id : str  = ''
    updated : bool = False
    message : str  = ''
