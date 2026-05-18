# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Discovery__Orchestrator
# Pulls current IAM state via IAM__AWS__Client and returns a flat list of
# nodes + edges ready for Iam__Graph__Builder.  Does NOT write to disk.
#
# Scope (Phases 1+3): roles only.  Users, groups, and standalone managed
# policies are scaffolded but left as empty lists until Phase 2 / v0.2.30.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client                        import IAM__AWS__Client
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node          import Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Edge          import Schema__IAM__Graph__Edge
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type               import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Edge__Type               import Enum__IAM__Edge__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth           import Enum__IAM__Scope__Breadth
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id        import Safe_Str__IAM__Node__Id

# ── AWS-default role detection heuristics ─────────────────────────────────────

_AWS_DEFAULT_NAME_PREFIXES = (
    'AWSServiceRole',
    'aws-service-role',
    'AWS_Events_Invoke',
    'AWSReservedSSO_',
    'OrganizationAccountAccessRole',
    'AWSControlTower',
)

_SERVICE_LINKED_SUFFIX = '/aws-service-role/'


def _is_aws_default(role_name: str, role_arn: str) -> bool:
    for prefix in _AWS_DEFAULT_NAME_PREFIXES:
        if role_name.startswith(prefix):
            return True
    if _SERVICE_LINKED_SUFFIX in role_arn:
        return True
    return False


def _is_service_linked(role_arn: str) -> bool:
    return _SERVICE_LINKED_SUFFIX in role_arn


def _scope_breadth(statements: list) -> Enum__IAM__Scope__Breadth:          # inspect inline policies
    for stmt in statements:
        actions   = stmt.get('Action', [])
        resources = stmt.get('Resource', [])
        if isinstance(actions, str):
            actions = [actions]
        if isinstance(resources, str):
            resources = [resources]
        for a in actions:
            if a in ('*', 'sts:*', 's3:*'):
                return Enum__IAM__Scope__Breadth.WILDCARD
        for r in resources:
            if r == '*':
                return Enum__IAM__Scope__Breadth.WILDCARD
        for a in actions:
            if a.endswith('*'):
                return Enum__IAM__Scope__Breadth.PREFIX_SCOPED
        for r in resources:
            if r.endswith('*'):
                return Enum__IAM__Scope__Breadth.PREFIX_SCOPED
    return Enum__IAM__Scope__Breadth.SPECIFIC


class Iam__Discovery__Orchestrator(Type_Safe):

    iam_client : IAM__AWS__Client

    def setup(self):                                                         # allow subclass injection
        if self.iam_client is None:
            self.iam_client = IAM__AWS__Client()
        return self

    # ── public ────────────────────────────────────────────────────────────────

    def discover_nodes(self) -> List__Schema__IAM__Graph__Node:
        self.setup()
        nodes = List__Schema__IAM__Graph__Node()
        for role in self.iam_client.list_roles():
            name      = str(role.role_name)
            arn       = str(role.role_arn)
            node_id   = arn if arn else f'role:{name}'
            node = Schema__IAM__Graph__Node(
                node_id           = Safe_Str__IAM__Node__Id(node_id),
                node_type         = Enum__IAM__Node__Type.ROLE,
                name              = name,
                arn               = arn,
                created_at        = role.created_at,
                last_used         = role.last_used,
                scope_breadth     = Enum__IAM__Scope__Breadth.SPECIFIC,
                is_aws_default    = _is_aws_default(name, arn),
                is_service_linked = _is_service_linked(arn),
                trust_principal   = str(role.trust_service),
            )
            nodes.append(node)
        return nodes

    def discover_edges(self, nodes: List__Schema__IAM__Graph__Node) -> List__Schema__IAM__Graph__Edge:
        self.setup()
        edges = List__Schema__IAM__Graph__Edge()
        for node in nodes:
            if node.node_type != Enum__IAM__Node__Type.ROLE:
                continue
            role_name = node.name
            full_role = self.iam_client.get_role(role_name)
            if full_role is None:
                continue
            for policy in full_role.inline_policies:
                policy_id  = f'inline:{role_name}:policy'
                edge = Schema__IAM__Graph__Edge(
                    source_id = Safe_Str__IAM__Node__Id(node.arn or f'role:{role_name}'),
                    target_id = Safe_Str__IAM__Node__Id(policy_id),
                    edge_type = Enum__IAM__Edge__Type.INLINE_POLICY,
                    label     = 'inline',
                )
                edges.append(edge)
            for arn in full_role.managed_policy_arns:
                edge = Schema__IAM__Graph__Edge(
                    source_id = Safe_Str__IAM__Node__Id(node.arn or f'role:{role_name}'),
                    target_id = Safe_Str__IAM__Node__Id(str(arn)),
                    edge_type = Enum__IAM__Edge__Type.MANAGED_POLICY,
                    label     = str(arn).split('/')[-1],
                )
                edges.append(edge)
        return edges
