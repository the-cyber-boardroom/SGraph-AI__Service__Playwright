# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Start__Request
# Body for POST /api/nodes/{node_id}/pods — starts a pod on the named node.
# ports/env are passed through as raw JSON by Pod__Manager; not typed here
# because Type_Safe__Dict cannot be converted to a Pydantic schema by
# osbot_fast_api's Type_Safe__To__BaseModel converter.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe


class Schema__Pod__Start__Request(Type_Safe):
    name    : str = ''
    image   : str = ''
    type_id : str = ''
