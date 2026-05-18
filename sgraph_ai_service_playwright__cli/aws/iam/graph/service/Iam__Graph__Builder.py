# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Graph__Builder
# Converts the raw node + edge lists from Iam__Discovery__Orchestrator into a
# dictionary-serialisable payload ready for Iam__Graph__Vault__Writer.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type               import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Snapshot      import Schema__IAM__Graph__Snapshot
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Snapshot__Id    import Safe_Str__IAM__Snapshot__Id


class Iam__Graph__Builder(Type_Safe):

    # ── public ────────────────────────────────────────────────────────────────

    def build_snapshot_meta(self,
                            snapshot_id : str,
                            nodes       : List__Schema__IAM__Graph__Node,
                            edges       : List__Schema__IAM__Graph__Edge,
                            captured_at : str = '',
                            account_id  : str = '',
                            region      : str = '') -> Schema__IAM__Graph__Snapshot:
        role_count   = sum(1 for n in nodes if n.node_type == Enum__IAM__Node__Type.ROLE)
        policy_count = sum(1 for n in nodes if n.node_type == Enum__IAM__Node__Type.POLICY)
        user_count   = sum(1 for n in nodes if n.node_type == Enum__IAM__Node__Type.USER)
        group_count  = sum(1 for n in nodes if n.node_type == Enum__IAM__Node__Type.GROUP)
        return Schema__IAM__Graph__Snapshot(
            snapshot_id    = Safe_Str__IAM__Snapshot__Id(snapshot_id),
            captured_at    = captured_at,
            role_count     = role_count,
            policy_count   = policy_count,
            user_count     = user_count,
            group_count    = group_count,
            edge_count     = len(edges),
            aws_account_id = account_id,
            region         = region,
        )

    def nodes_to_dict_list(self, nodes: List__Schema__IAM__Graph__Node) -> list:
        result = []
        for n in nodes:
            result.append(dict(
                node_id          = str(n.node_id),
                node_type        = str(n.node_type),
                name             = n.name,
                arn              = n.arn,
                created_at       = n.created_at,
                last_used        = n.last_used,
                scope_breadth    = str(n.scope_breadth),
                is_aws_default   = n.is_aws_default,
                is_service_linked= n.is_service_linked,
                trust_principal  = n.trust_principal,
                tags_json        = n.tags_json,
            ))
        return result

    def edges_to_dict_list(self, edges: List__Schema__IAM__Graph__Edge) -> list:
        result = []
        for e in edges:
            result.append(dict(
                source_id = str(e.source_id),
                target_id = str(e.target_id),
                edge_type = str(e.edge_type),
                label     = e.label,
            ))
        return result
