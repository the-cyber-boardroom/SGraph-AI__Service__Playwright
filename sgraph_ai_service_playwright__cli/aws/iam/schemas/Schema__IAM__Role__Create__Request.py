# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Role__Create__Request
# Input to IAM__AWS__Client.create_role(). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service     import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Policy         import Schema__IAM__Policy


class Schema__IAM__Role__Create__Request(Type_Safe):
    role_name      : Safe_Str__IAM__Role_Name
    trust_service  : Enum__IAM__Trust__Service = Enum__IAM__Trust__Service.LAMBDA
    description    : str                       = ''
    inline_policy  : Optional[Schema__IAM__Policy]  = None   # if set, attached as the role's single inline policy
    policy_name    : str                       = 'permissions'  # name for the inline policy document
