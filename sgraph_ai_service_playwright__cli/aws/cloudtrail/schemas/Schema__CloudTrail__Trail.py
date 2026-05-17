# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Schema__CloudTrail__Trail
# Summary schema for a single CloudTrail trail configuration.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.cloudtrail.primitives.Safe_Str__CloudTrail__Trail_Name import Safe_Str__CloudTrail__Trail_Name
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket       import Safe_Str__S3__Bucket


class Schema__CloudTrail__Trail(Type_Safe):
    name                         : Safe_Str__CloudTrail__Trail_Name
    s3_bucket_name               : Safe_Str__S3__Bucket
    home_region                  : Safe_Str__AWS__Region
    is_multi_region_trail        : bool = False
    include_global_service_events: bool = False
    log_file_validation_enabled  : bool = False
    trail_arn                    : Safe_Str__AWS__ARN
    is_logging                   : bool = False
