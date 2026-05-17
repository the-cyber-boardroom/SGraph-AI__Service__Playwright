# ═══════════════════════════════════════════════════════════════════════════════
# Tests — IAM__AWS__Client (via in-memory fake)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service         import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name     import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory import IAM__AWS__Client__In_Memory


def _client() -> IAM__AWS__Client__In_Memory:
    return IAM__AWS__Client__In_Memory()


class Test__IAM__AWS__Client:

    def test_1__list_roles_empty(self):
        assert list(_client().list_roles()) == []

    def test_2__create_role(self):
        c   = _client()
        req = Schema__IAM__Role__Create__Request(
                  role_name    = Safe_Str__IAM__Role_Name('test-role'),
                  trust_service= Enum__IAM__Trust__Service.LAMBDA)
        resp = c.create_role(req)
        assert resp.created is True
        assert 'test-role' in str(resp.role_name)
        assert 'arn:aws:iam' in str(resp.role_arn)

    def test_3__create_role_idempotent_returns_existing(self):
        c   = _client()
        req = Schema__IAM__Role__Create__Request(
                  role_name    = Safe_Str__IAM__Role_Name('my-role'),
                  trust_service= Enum__IAM__Trust__Service.EC2)
        c.create_role(req)
        resp2 = c.create_role(req)
        assert resp2.created is False
        assert resp2.message == 'already exists'

    def test_4__get_role_returns_schema(self):
        c   = _client()
        req = Schema__IAM__Role__Create__Request(
                  role_name    = Safe_Str__IAM__Role_Name('fetch-me'),
                  trust_service= Enum__IAM__Trust__Service.LAMBDA)
        c.create_role(req)
        role = c.get_role('fetch-me')
        assert role is not None
        assert str(role.role_name) == 'fetch-me'
        assert role.trust_service  == Enum__IAM__Trust__Service.LAMBDA

    def test_5__get_role_missing_returns_none(self):
        assert _client().get_role('no-such-role') is None

    def test_6__list_roles_returns_created_roles(self):
        c = _client()
        for name in ('role-a', 'role-b', 'role-c'):
            c.create_role(Schema__IAM__Role__Create__Request(
                role_name=Safe_Str__IAM__Role_Name(name),
                trust_service=Enum__IAM__Trust__Service.LAMBDA))
        roles = list(c.list_roles())
        assert len(roles) == 3

    def test_7__list_roles_prefix_filter(self):
        c = _client()
        for name in ('sg-role-a', 'sg-role-b', 'other-role'):
            c.create_role(Schema__IAM__Role__Create__Request(
                role_name=Safe_Str__IAM__Role_Name(name),
                trust_service=Enum__IAM__Trust__Service.LAMBDA))
        roles = list(c.list_roles(prefix='sg-'))
        assert len(roles) == 2

    def test_8__delete_role(self):
        c   = _client()
        req = Schema__IAM__Role__Create__Request(
                  role_name    = Safe_Str__IAM__Role_Name('to-delete'),
                  trust_service= Enum__IAM__Trust__Service.LAMBDA)
        c.create_role(req)
        assert c.role_exists('to-delete') is True
        c.delete_role('to-delete')
        assert c.role_exists('to-delete') is False

    def test_9__attach_and_detach_managed_policy(self):
        c   = _client()
        req = Schema__IAM__Role__Create__Request(
                  role_name    = Safe_Str__IAM__Role_Name('attach-test'),
                  trust_service= Enum__IAM__Trust__Service.LAMBDA)
        c.create_role(req)
        arn = 'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'
        assert c.attach_managed_policy('attach-test', arn) is True
        role = c.get_role('attach-test')
        assert any(str(p) == arn for p in role.managed_policy_arns)
        assert c.detach_managed_policy('attach-test', arn) is True
        role2 = c.get_role('attach-test')
        assert all(str(p) != arn for p in role2.managed_policy_arns)

    def test_10__put_inline_policy_and_retrieve(self):
        from sgraph_ai_service_playwright__cli.aws.iam.service.templates.Waker__Policy__Template import Waker__Policy__Template
        c   = _client()
        req = Schema__IAM__Role__Create__Request(
                  role_name    = Safe_Str__IAM__Role_Name('policy-test'),
                  trust_service= Enum__IAM__Trust__Service.LAMBDA)
        c.create_role(req)
        policy = Waker__Policy__Template().build()
        ok     = c.put_inline_policy('policy-test', 'permissions', policy)
        assert ok is True
        role = c.get_role('policy-test')
        assert len(role.inline_policies) == 1
