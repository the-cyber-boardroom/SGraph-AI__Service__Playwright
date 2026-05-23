# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__TUI__Status
# The Status / Deployed-code surface snapshot: locally-derivable reality (sink
# counts, rule count, engine + ruleset version, banned-ip count, node readiness).
# The materialised engine code + sink dir are passed to the render separately (raw
# text, not Safe_Str-sanitised). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Version import Safe_Str__Sentinel__Version


class Schema__Sentinel__TUI__Status(Type_Safe):
    node_available  : bool      = False
    record_count    : int       = 0
    allow_count     : int       = 0
    block_count     : int       = 0
    rule_count      : int       = 0
    banned_ip_count : int       = 0
    engine_version  : Safe_Str__Sentinel__Version
    ruleset_version : Safe_Str__Sentinel__Version
