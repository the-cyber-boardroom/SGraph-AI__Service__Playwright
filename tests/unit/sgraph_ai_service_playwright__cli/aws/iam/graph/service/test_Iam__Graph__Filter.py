# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Iam__Graph__Filter
# Unit tests for unused / pattern / aws-default predicates. All in-memory.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node  import List__Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type                 import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth             import Enum__IAM__Scope__Breadth
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id          import Safe_Str__IAM__Node__Id
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node            import Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Filter                  import Iam__Graph__Filter


def _make_node(name: str, last_used: str = '', is_aws_default: bool = False,
               is_service_linked: bool = False) -> Schema__IAM__Graph__Node:
    return Schema__IAM__Graph__Node(
        node_id          = Safe_Str__IAM__Node__Id(f'arn:aws:iam::123456789012:role/{name}'),
        node_type        = Enum__IAM__Node__Type.ROLE,
        name             = name,
        arn              = f'arn:aws:iam::123456789012:role/{name}',
        created_at       = '2025-01-01T00:00:00+00:00',
        last_used        = last_used,
        scope_breadth    = Enum__IAM__Scope__Breadth.SPECIFIC,
        is_aws_default   = is_aws_default,
        is_service_linked= is_service_linked,
        trust_principal  = 'lambda.amazonaws.com',
    )


def _node_list(*nodes) -> List__Schema__IAM__Graph__Node:
    result = List__Schema__IAM__Graph__Node()
    for n in nodes:
        result.append(n)
    return result


class Test__Iam__Graph__Filter:

    def test_1__filter_unused__never_used_included(self):
        node  = _make_node('sg-never-used', last_used='')
        nodes = _node_list(node)
        result = Iam__Graph__Filter().filter_unused(nodes, days=90)
        assert len(result) == 1
        assert result[0].name == 'sg-never-used'

    def test_2__filter_unused__recent_role_excluded(self):
        node  = _make_node('sg-recent', last_used='2026-05-10T00:00:00+00:00')  # within 90 days of 2026-05-17
        nodes = _node_list(node)
        result = Iam__Graph__Filter().filter_unused(nodes, days=90)
        assert len(result) == 0

    def test_3__filter_unused__stale_role_included(self):
        node  = _make_node('sg-stale', last_used='2025-01-01T00:00:00+00:00')   # >90 days before 2026-05-17
        nodes = _node_list(node)
        result = Iam__Graph__Filter().filter_unused(nodes, days=90)
        assert len(result) == 1
        assert result[0].name == 'sg-stale'

    def test_4__filter_pattern__matches(self):
        nodes = _node_list(
            _make_node('sg-waker-role'),
            _make_node('sg-lambda-role'),
            _make_node('AWSReservedSSO_admin'),
        )
        result = Iam__Graph__Filter().filter_pattern(nodes, 'sg-*')
        assert len(result) == 2
        names = {n.name for n in result}
        assert 'sg-waker-role' in names
        assert 'sg-lambda-role' in names

    def test_5__filter_pattern__no_match(self):
        nodes  = _node_list(_make_node('unrelated-role'))
        result = Iam__Graph__Filter().filter_pattern(nodes, 'sg-*')
        assert len(result) == 0

    def test_6__filter_aws_default__finds_service_linked(self):
        nodes = _node_list(
            _make_node('user-created-role'),
            _make_node('AWSServiceRole', is_aws_default=True),
            _make_node('svc-linked',      is_service_linked=True),
        )
        result = Iam__Graph__Filter().filter_aws_default(nodes)
        assert len(result) == 2
        names = {n.name for n in result}
        assert 'AWSServiceRole' in names
        assert 'svc-linked' in names

    def test_7__filter_aws_default__excludes_user_roles(self):
        nodes = _node_list(_make_node('my-app-role'))
        result = Iam__Graph__Filter().filter_aws_default(nodes)
        assert len(result) == 0

    def test_8__filter_unused__only_includes_role_type(self):
        from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type import Enum__IAM__Node__Type
        role   = _make_node('sg-role')
        policy = Schema__IAM__Graph__Node(
            node_id  = Safe_Str__IAM__Node__Id('arn:aws:iam::aws:policy/SomePolicy'),
            node_type= Enum__IAM__Node__Type.POLICY,
            name     = 'SomePolicy',
        )
        nodes  = _node_list(role, policy)
        result = Iam__Graph__Filter().filter_unused(nodes, days=90)
        types  = {n.node_type for n in result}
        assert Enum__IAM__Node__Type.POLICY not in types
