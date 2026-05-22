# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/s3/tui_api: Schema__S3__Params__Head_Object
# Params for the head_object action. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Key    import Safe_Str__S3__Key


class Schema__S3__Params__Head_Object(Type_Safe):
    bucket : Safe_Str__S3__Bucket                                                 # S3 bucket name
    key    : Safe_Str__S3__Key                                                    # full object key to stat
