# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__S3__Bucket
# One S3 bucket record. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket      import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Timestamp   import Safe_Str__S3__Timestamp
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Versioning  import Safe_Str__S3__Versioning


class Schema__S3__Bucket(Type_Safe):
    name          : Safe_Str__S3__Bucket
    creation_date : Safe_Str__S3__Timestamp                                         # ISO-8601 string from S3
    region        : Safe_Str__AWS__Region                                           # populated by get_bucket_region
    versioning    : Safe_Str__S3__Versioning                                        # Enabled | Suspended | Disabled
    object_count  : int = 0
    total_bytes   : int = 0
