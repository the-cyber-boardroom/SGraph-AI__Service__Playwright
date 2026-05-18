# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Graph__Edge
# A directed relationship between two IAM graph nodes.
# Pure data. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Edge__Type        import Enum__IAM__Edge__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id import Safe_Str__IAM__Node__Id


class Schema__IAM__Graph__Edge(Type_Safe):
    source_id  : Safe_Str__IAM__Node__Id                                   # from node
    target_id  : Safe_Str__IAM__Node__Id                                   # to node
    edge_type  : Enum__IAM__Edge__Type = Enum__IAM__Edge__Type.MANAGED_POLICY
    label      : str                   = ''                                # optional display label
