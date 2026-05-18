# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Graph__Node
# A single vertex in the IAM graph: role, policy, user, or group.
# Pure data. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type        import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth    import Enum__IAM__Scope__Breadth
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id import Safe_Str__IAM__Node__Id


class Schema__IAM__Graph__Node(Type_Safe):
    node_id          : Safe_Str__IAM__Node__Id                                   # ARN or synthetic id
    node_type        : Enum__IAM__Node__Type     = Enum__IAM__Node__Type.ROLE
    name             : str                       = ''                            # human-readable name
    arn              : str                       = ''                            # ARN (may equal node_id)
    created_at       : str                       = ''                            # ISO-8601
    last_used        : str                       = ''                            # ISO-8601; empty = never
    scope_breadth    : Enum__IAM__Scope__Breadth = Enum__IAM__Scope__Breadth.SPECIFIC
    is_aws_default   : bool                      = False                         # AWS-managed/auto-created
    is_service_linked: bool                      = False                         # service-linked role
    trust_principal  : str                       = ''                            # trust policy principal
    tags_json        : str                       = ''                            # JSON-encoded tag map
