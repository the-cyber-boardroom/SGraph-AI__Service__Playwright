# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/s3/tui_api: Schema__S3__Params__List_Objects
# Params for the list_objects action. Type_Safe validates on construction; the
# Tui_Api__Schema__Builder emits its JSON Schema for the model. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Prefix import Safe_Str__S3__Prefix


class Schema__S3__Params__List_Objects(Type_Safe):
    bucket    : Safe_Str__S3__Bucket                                              # S3 bucket name to list
    prefix    : Safe_Str__S3__Prefix = Safe_Str__S3__Prefix('')                   # key prefix to list under
    recursive : bool                 = False                                      # recurse into sub-prefixes (drop the '/' delimiter)
