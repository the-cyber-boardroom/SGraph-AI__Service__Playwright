# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Schema__ECR__Repo
# Summary schema for one ECR repository. Aggregates count + total bytes across
# images so the CLI can render the repo summary table without a second call.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name import Safe_Str__ECR__Repo_Name


class Schema__ECR__Repo(Type_Safe):
    name                 : Safe_Str__ECR__Repo_Name
    arn                  : str  = ''
    registry_id          : str  = ''
    created_at           : str  = ''                                            # ISO-8601 from boto3 datetime
    image_count          : int  = 0
    total_size_bytes     : int  = 0
    lifecycle_policy     : str  = ''                                            # JSON string or empty
    image_tag_mutability : str  = ''
    scan_on_push         : bool = False
