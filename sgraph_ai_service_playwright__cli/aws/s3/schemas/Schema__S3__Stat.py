# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__S3__Stat
# Full object metadata from HeadObject. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.enums.Enum__S3__Storage__Class      import Enum__S3__Storage__Class
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket     import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Content_Type import Safe_Str__S3__Content_Type
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Encryption import Safe_Str__S3__Encryption
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__ETag       import Safe_Str__S3__ETag
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Key        import Safe_Str__S3__Key
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Timestamp  import Safe_Str__S3__Timestamp
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Version_Id import Safe_Str__S3__Version_Id


class Schema__S3__Stat(Type_Safe):
    bucket        : Safe_Str__S3__Bucket
    key           : Safe_Str__S3__Key
    size          : int                       = 0
    last_modified : Safe_Str__S3__Timestamp                                        # ISO-8601 string
    etag          : Safe_Str__S3__ETag
    storage_class : Enum__S3__Storage__Class  = Enum__S3__Storage__Class.STANDARD
    content_type  : Safe_Str__S3__Content_Type
    encryption    : Safe_Str__S3__Encryption                                       # e.g. AES256 or aws:kms
    version_id    : Safe_Str__S3__Version_Id
