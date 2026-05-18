# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Role__Create__Response
# Response from IAM__AWS__Client.create_role(). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn  import Safe_Str__IAM__Role_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name import Safe_Str__IAM__Role_Name


class Schema__IAM__Role__Create__Response(Type_Safe):
    role_name : Safe_Str__IAM__Role_Name
    role_arn  : Safe_Str__IAM__Role_Arn
    created   : bool = False
    message   : str  = ''
