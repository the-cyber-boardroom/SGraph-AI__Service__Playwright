# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Mitm__Script__Response
# Response for PUT /api/specs/firefox/{node_id}/mitm-script
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Schema__Firefox__Mitm__Script__Response(Type_Safe):
    node_id  : str  = ''
    uploaded : bool = False
    message  : str  = ''
