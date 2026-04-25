# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Inventory__Load__Request
# Inputs for `sp el lets cf inventory load`. Default scope (no flags) is
# "today UTC" — the service resolves the prefix from the current UTC date.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket   import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix import Safe_Str__S3__Key__Prefix


class Schema__Inventory__Load__Request(Type_Safe):
    bucket           : Safe_Str__S3__Bucket                                         # The CloudFront-realtime bucket; service has a default if empty
    prefix           : Safe_Str__S3__Key__Prefix                                    # Empty → service resolves "cloudfront-realtime/{today UTC}/"
    all              : bool                          = False                        # Explicit full-bucket scan; ignored when prefix is set
    max_keys         : int                           = 0                            # 0 = unlimited; otherwise stop after N objects
    run_id           : Safe_Str__Pipeline__Run__Id                                  # Empty → service auto-generates
    stack_name       : Safe_Str__Elastic__Stack__Name                               # Empty → auto-pick (single stack) or prompt (multi)
    dry_run          : bool                          = False                        # List + parse only; skip the bulk-post step
