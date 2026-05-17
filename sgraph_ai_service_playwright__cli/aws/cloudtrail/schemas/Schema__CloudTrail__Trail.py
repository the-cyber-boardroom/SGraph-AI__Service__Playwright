# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Schema__CloudTrail__Trail
# Summary schema for a single CloudTrail trail configuration.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CloudTrail__Trail(Type_Safe):
    name                        : str  = ''
    s3_bucket_name              : str  = ''
    home_region                 : str  = ''
    is_multi_region_trail       : bool = False
    include_global_service_events: bool = False
    log_file_validation_enabled : bool = False
    trail_arn                   : str  = ''
    is_logging                  : bool = False
