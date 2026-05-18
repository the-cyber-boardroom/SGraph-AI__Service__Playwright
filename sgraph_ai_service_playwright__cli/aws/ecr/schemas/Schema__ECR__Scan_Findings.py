# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Schema__ECR__Scan_Findings
# Most-recent scan summary for one ECR image: status + completion timestamp +
# severity counts. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status   import Enum__ECR__Image_Scan_Status
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name    import Safe_Str__ECR__Repo_Name
from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Scan_Finding_Counts import Schema__ECR__Scan_Finding_Counts


class Schema__ECR__Scan_Findings(Type_Safe):
    repo_name    : Safe_Str__ECR__Repo_Name
    digest       : Safe_Str__ECR__Image_Digest
    status       : Enum__ECR__Image_Scan_Status      = Enum__ECR__Image_Scan_Status.UNKNOWN
    completed_at : str                               = ''                       # ISO-8601 from boto3 datetime
    counts       : Schema__ECR__Scan_Finding_Counts
