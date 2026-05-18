# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Schema__ECR__Image
# One ECR image: digest, tags, size, pushed_at, manifest media type, scan
# status. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status import Enum__ECR__Image_Scan_Status
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name    import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Tag          import Safe_Str__ECR__Tag


class Schema__ECR__Image(Type_Safe):
    repo_name           : Safe_Str__ECR__Repo_Name
    digest              : Safe_Str__ECR__Image_Digest
    tags                : list[Safe_Str__ECR__Tag]
    size_bytes          : int                          = 0
    pushed_at           : str                          = ''                     # ISO-8601 from boto3 datetime
    manifest_media_type : str                          = ''
    scan_status         : Enum__ECR__Image_Scan_Status = Enum__ECR__Image_Scan_Status.UNKNOWN
