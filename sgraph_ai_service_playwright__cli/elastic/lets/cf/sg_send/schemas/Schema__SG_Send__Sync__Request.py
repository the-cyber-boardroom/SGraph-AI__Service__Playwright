# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__SG_Send__Sync__Request
# Input for `sp el lets cf sg-send sync`.  Covers one calendar date (defaults
# to today UTC) — runs inventory load for that date's S3 prefix, then runs
# events load --from-inventory capped by max_files.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket import Safe_Str__S3__Bucket


class Schema__SG_Send__Sync__Request(Type_Safe):
    sync_date  : Safe_Str__Text                     # "YYYY-MM-DD"; empty → today UTC
    max_files  : int  = 0                           # Cap on events load; 0 = unlimited
    dry_run    : bool = False
    bucket     : Safe_Str__S3__Bucket               # Empty → SG_SEND__DEFAULT_BUCKET
    region     : Safe_Str__AWS__Region
    stack_name : Safe_Str__Elastic__Stack__Name     # Empty → auto-pick
