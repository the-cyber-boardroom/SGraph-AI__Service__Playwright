# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__IAM__Statement
# Verifies the least-privilege contract on the statement schema:
#   • bare "*" action rejected by Safe_Str__Aws__Action
#   • wildcard resource requires allow_wildcard_resource=True flag
#   • power actions without condition_json are flagged by auditor (not schema)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Action   import List__Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Resource import List__Safe_Str__Aws__Resource
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Action          import Safe_Str__Aws__Action
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Resource        import Safe_Str__Aws__Resource
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Statement            import Schema__IAM__Statement


def _actions(*names) -> List__Safe_Str__Aws__Action:
    col = List__Safe_Str__Aws__Action()
    for n in names:
        col.append(Safe_Str__Aws__Action(n))
    return col


def _resources(*values) -> List__Safe_Str__Aws__Resource:
    col = List__Safe_Str__Aws__Resource()
    for v in values:
        col.append(Safe_Str__Aws__Resource(v))
    return col


class Test__Schema__IAM__Statement:

    def test_1__bare_wildcard_action_rejected_at_primitive(self):
        with pytest.raises(Exception):
            Safe_Str__Aws__Action('*')                                               # no colon → regex mismatch

    def test_2__service_wildcard_action_allowed(self):
        a = Safe_Str__Aws__Action('iam:*')
        assert str(a) == 'iam:*'

    def test_3__specific_action_allowed(self):
        a = Safe_Str__Aws__Action('ec2:StartInstances')
        assert str(a) == 'ec2:StartInstances'

    def test_4__trailing_wildcard_action_allowed(self):
        a = Safe_Str__Aws__Action('ec2:Describe*')
        assert str(a) == 'ec2:Describe*'

    def test_5__bare_wildcard_resource_allowed_by_primitive(self):
        r = Safe_Str__Aws__Resource('*')                                             # schema struct allows it; auditor flags it
        assert str(r) == '*'

    def test_6__arn_resource_allowed(self):
        r = Safe_Str__Aws__Resource('arn:aws:ec2:*:*:instance/*')
        assert str(r) == 'arn:aws:ec2:*:*:instance/*'

    def test_7__allow_wildcard_resource_defaults_to_false(self):
        stmt = Schema__IAM__Statement(actions=_actions('ec2:DescribeInstances'),
                                       resources=_resources('*'))
        assert stmt.allow_wildcard_resource is False

    def test_8__allow_wildcard_resource_explicit_opt_in(self):
        stmt = Schema__IAM__Statement(actions=_actions('ec2:DescribeInstances'),
                                       resources=_resources('*'),
                                       allow_wildcard_resource=True)
        assert stmt.allow_wildcard_resource is True

    def test_9__condition_json_defaults_to_empty(self):
        stmt = Schema__IAM__Statement(actions=_actions('ec2:StartInstances'),
                                       resources=_resources('arn:aws:ec2:*:*:instance/*'))
        assert stmt.condition_json == ''

    def test_10__condition_json_stored_as_string(self):
        import json
        cond = json.dumps({'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}})
        stmt = Schema__IAM__Statement(actions=_actions('ec2:StartInstances'),
                                       resources=_resources('arn:aws:ec2:*:*:instance/*'),
                                       condition_json=cond)
        assert 'vault-app' in stmt.condition_json

    def test_11__effect_defaults_to_allow(self):
        stmt = Schema__IAM__Statement(actions=_actions('logs:PutLogEvents'),
                                       resources=_resources('arn:aws:logs:*:*:*'))
        assert stmt.effect == 'Allow'
