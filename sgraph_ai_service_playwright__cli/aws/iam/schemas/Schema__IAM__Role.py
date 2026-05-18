# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Role
# One IAM role with its attached inline policies + managed policy ARNs.
# Pure data. Populated by IAM__AWS__Client.get_role().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__IAM__Policy_Arn  import List__Safe_Str__IAM__Policy_Arn
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Policy        import List__Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service              import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn           import Safe_Str__IAM__Role_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name          import Safe_Str__IAM__Role_Name


class Schema__IAM__Role(Type_Safe):
    role_name            : Safe_Str__IAM__Role_Name
    role_arn             : Safe_Str__IAM__Role_Arn
    trust_service        : Enum__IAM__Trust__Service      = Enum__IAM__Trust__Service.LAMBDA
    inline_policies      : List__Schema__IAM__Policy                  # via put_role_policy
    managed_policy_arns  : List__Safe_Str__IAM__Policy_Arn            # via attach_role_policy
    created_at           : str                            = ''        # ISO-8601 from IAM CreateDate
    last_used            : str                            = ''        # ISO-8601; empty = never used
