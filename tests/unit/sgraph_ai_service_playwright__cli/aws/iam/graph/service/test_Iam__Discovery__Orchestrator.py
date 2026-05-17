# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Iam__Discovery__Orchestrator
# Verifies discover_nodes + discover_edges with fake IAM data. No real AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service              import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type            import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name          import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request   import Schema__IAM__Role__Create__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Discovery__Orchestrator__In_Memory import Iam__Discovery__Orchestrator__In_Memory


def _orchestrator_with_roles(*names) -> Iam__Discovery__Orchestrator__In_Memory:
    orc = Iam__Discovery__Orchestrator__In_Memory()
    for name in names:
        orc.iam_client.create_role(Schema__IAM__Role__Create__Request(
            role_name    = Safe_Str__IAM__Role_Name(name),
            trust_service= Enum__IAM__Trust__Service.LAMBDA,
        ))
    return orc


class Test__Iam__Discovery__Orchestrator:

    def test_1__discover_nodes_empty(self):
        orc   = Iam__Discovery__Orchestrator__In_Memory()
        nodes = orc.discover_nodes()
        assert len(nodes) == 0

    def test_2__discover_nodes_single_role(self):
        orc   = _orchestrator_with_roles('sg-waker-role')
        nodes = orc.discover_nodes()
        assert len(nodes) == 1
        assert nodes[0].name == 'sg-waker-role'
        assert nodes[0].node_type == Enum__IAM__Node__Type.ROLE

    def test_3__discover_nodes_multiple_roles(self):
        orc   = _orchestrator_with_roles('role-a', 'role-b', 'role-c')
        nodes = orc.discover_nodes()
        assert len(nodes) == 3
        names = {n.name for n in nodes}
        assert names == {'role-a', 'role-b', 'role-c'}

    def test_4__discover_edges_no_policies(self):
        orc   = _orchestrator_with_roles('sg-empty-role')
        nodes = orc.discover_nodes()
        edges = orc.discover_edges(nodes)
        assert len(edges) == 0

    def test_5__discover_edges_with_managed_policy(self):
        orc = _orchestrator_with_roles('sg-ec2-role')
        orc.iam_client.attach_managed_policy(
            'sg-ec2-role', 'arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess')
        nodes = orc.discover_nodes()
        edges = orc.discover_edges(nodes)
        assert len(edges) == 1
        assert edges[0].label == 'AmazonEC2ReadOnlyAccess'

    def test_6__aws_default_flag_set_for_service_roles(self):
        orc = Iam__Discovery__Orchestrator__In_Memory()
        orc.iam_client._fake._roles['AWSServiceRoleForEC2'] = {
            'RoleName'                : 'AWSServiceRoleForEC2',
            'Arn'                     : 'arn:aws:iam::123456789012:role/aws-service-role/ec2.amazonaws.com/AWSServiceRoleForEC2',
            'AssumeRolePolicyDocument': {'Statement': [{'Principal': {'Service': 'ec2.amazonaws.com'}, 'Effect': 'Allow', 'Action': 'sts:AssumeRole'}]},
            'CreateDate'              : '2025-01-01T00:00:00+00:00',
            'RoleLastUsed'            : {},
        }
        orc.iam_client._fake._inline_policies['AWSServiceRoleForEC2']     = {}
        orc.iam_client._fake._managed_attachments['AWSServiceRoleForEC2'] = []
        nodes = orc.discover_nodes()
        svc_node = next(n for n in nodes if 'AWSServiceRole' in n.name)
        assert svc_node.is_service_linked is True
