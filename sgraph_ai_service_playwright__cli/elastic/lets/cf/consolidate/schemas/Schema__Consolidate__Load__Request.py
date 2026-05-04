# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Consolidate__Load__Request
# Inputs for `sp el lets cf consolidate load`.
# Service auto-resolves bucket / run_id when empty.
# `date_iso` drives both the source prefix scan and the output S3 path.
# `compat_region` selects which lets/ workflow region to write to; defaults to
# the CF-realtime consolidation region.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket        import Safe_Str__S3__Bucket


DEFAULT_COMPAT_REGION = 'raw-cf-to-consolidated'


class Schema__Consolidate__Load__Request(Type_Safe):
    bucket         : Safe_Str__S3__Bucket                                            # Source + output bucket; service has a default
    date_iso       : Safe_Str__Text                                                  # "YYYY-MM-DD"; empty → today UTC
    compat_region  : Safe_Str__Text    = Safe_Str__Text(DEFAULT_COMPAT_REGION)       # compat-region subfolder under lets/
    from_inventory : bool              = True                                        # Build queue from inventory manifest (default)
    max_files      : int               = 0                                           # 0 = unlimited
    run_id         : Safe_Str__Pipeline__Run__Id                                     # Empty → auto-generated
    stack_name     : Safe_Str__Elastic__Stack__Name                                  # For journal + progress labelling
    region         : Safe_Str__AWS__Region                                           # Empty → boto3 default chain
    dry_run        : bool              = False                                       # Build queue, skip all S3 writes and ES updates
