# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__S3__Bucket
# One S3 bucket record. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket    import Safe_Str__S3__Bucket


class Schema__S3__Bucket(Type_Safe):
    name          : Safe_Str__S3__Bucket
    creation_date : str = ''                                                      # ISO-8601 string from S3
    region        : str = ''                                                      # populated by get_bucket_region
    versioning    : str = ''                                                      # Enabled | Suspended | Disabled
    object_count  : int = 0
    total_bytes   : int = 0
