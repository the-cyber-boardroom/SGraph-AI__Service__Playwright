# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Schema__ECR__Prune__Plan
# Output of ECR__Prune__Planner.plan(): the candidate-deletion set + summary.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ecr.collections.List__Schema__ECR__Image import List__Schema__ECR__Image
from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name  import Safe_Str__ECR__Repo_Name


class Schema__ECR__Prune__Plan(Type_Safe):
    repo_name      : Safe_Str__ECR__Repo_Name
    to_delete      : List__Schema__ECR__Image
    kept_count     : int = 0
    policy_summary : str = ''
