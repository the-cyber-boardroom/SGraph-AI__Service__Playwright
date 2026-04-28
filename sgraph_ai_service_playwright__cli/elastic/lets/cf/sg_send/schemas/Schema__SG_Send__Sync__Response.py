# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__SG_Send__Sync__Response
# Unified result from `SG_Send__Orchestrator.sync()`.  Embeds both sub-phase
# responses so callers can drill into per-slice stats without a second query.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Response import Schema__Inventory__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Response       import Schema__Events__Load__Response


class Schema__SG_Send__Sync__Response(Type_Safe):
    sync_date           : Safe_Str__Text                    # "YYYY-MM-DD" of the synced day
    inventory_response  : Schema__Inventory__Load__Response # full slice-1 result
    events_response     : Schema__Events__Load__Response    # full slice-2 result
    s3_calls_total      : int  = 0                          # combined s3 call count
    elastic_calls_total : int  = 0                          # combined elastic call count
    wall_ms             : int  = 0                          # total wall-clock milliseconds
    dry_run             : bool = False
