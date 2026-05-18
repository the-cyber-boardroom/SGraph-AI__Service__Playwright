# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish setup tests — Setup__IAM
# In-memory tests for all five verbs: check / status / create / update / delete
# No mocks. No patches. No AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import pytest
from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client import IAM__AWS__Client
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State    import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.service.Setup__IAM            import (
    Setup__IAM, WAKER_ROLE_NAME, WAKER_POLICY_NAME)


# ── In-memory IAM client ──────────────────────────────────────────────────────

class _Fake_IAM_Boto:
    """Minimal boto3-alike IAM client that raises proper ClientError."""

    def __init__(self):
        self._roles               = {}
        self._inline_policies     = {}
        self._managed_attachments = {}

    def _no_such_entity(self, name: str):
        raise ClientError(
            {'Error': {'Code': 'NoSuchEntity', 'Message': f'{name} not found'}},
            'GetRole',
        )

    def get_paginator(self, method: str):
        return _FakePaginator(self, method)

    def get_role(self, RoleName: str):
        if RoleName not in self._roles:
            self._no_such_entity(RoleName)
        return {'Role': self._roles[RoleName]}

    def create_role(self, RoleName: str, AssumeRolePolicyDocument: str, Description: str = '', **_):
        if RoleName in self._roles:
            raise ClientError({'Error': {'Code': 'EntityAlreadyExists', 'Message': ''}}, 'CreateRole')
        arn = f'arn:aws:iam::123456789012:role/{RoleName}'
        self._roles[RoleName] = {
            'RoleName'               : RoleName,
            'Arn'                    : arn,
            'AssumeRolePolicyDocument': json.loads(AssumeRolePolicyDocument),
            'CreateDate'             : '2026-05-17T00:00:00+00:00',
            'RoleLastUsed'           : {},
            'Description'            : Description,
        }
        self._inline_policies[RoleName]     = {}
        self._managed_attachments[RoleName] = []
        return {'Role': self._roles[RoleName]}

    def delete_role(self, RoleName: str, **_):
        if RoleName not in self._roles:
            self._no_such_entity(RoleName)
        del self._roles[RoleName]
        self._inline_policies.pop(RoleName, None)
        self._managed_attachments.pop(RoleName, None)

    def put_role_policy(self, RoleName: str, PolicyName: str, PolicyDocument: str, **_):
        if RoleName not in self._inline_policies:
            self._inline_policies[RoleName] = {}
        self._inline_policies[RoleName][PolicyName] = json.loads(PolicyDocument)

    def get_role_policy(self, RoleName: str, PolicyName: str, **_):
        policies = self._inline_policies.get(RoleName, {})
        if PolicyName not in policies:
            raise ClientError({'Error': {'Code': 'NoSuchEntity', 'Message': ''}}, 'GetRolePolicy')
        return {
            'RoleName'      : RoleName,
            'PolicyName'    : PolicyName,
            'PolicyDocument': policies[PolicyName],
        }

    def delete_role_policy(self, RoleName: str, PolicyName: str, **_):
        if RoleName in self._inline_policies:
            self._inline_policies[RoleName].pop(PolicyName, None)

    def attach_role_policy(self, RoleName: str, PolicyArn: str, **_):
        if RoleName not in self._managed_attachments:
            self._managed_attachments[RoleName] = []
        if PolicyArn not in self._managed_attachments[RoleName]:
            self._managed_attachments[RoleName].append(PolicyArn)

    def detach_role_policy(self, RoleName: str, PolicyArn: str, **_):
        lst = self._managed_attachments.get(RoleName, [])
        self._managed_attachments[RoleName] = [a for a in lst if a != PolicyArn]


class _FakePaginator:
    def __init__(self, client: _Fake_IAM_Boto, method: str):
        self._c = client
        self._m = method

    def paginate(self, **kwargs):
        if self._m == 'list_roles':
            yield {'Roles': list(self._c._roles.values())}
        elif self._m == 'list_role_policies':
            role  = kwargs.get('RoleName', '')
            names = list(self._c._inline_policies.get(role, {}).keys())
            yield {'PolicyNames': names}
        elif self._m == 'list_attached_role_policies':
            role = kwargs.get('RoleName', '')
            arns = self._c._managed_attachments.get(role, [])
            yield {'AttachedPolicies': [{'PolicyArn': a, 'PolicyName': a.split('/')[-1]} for a in arns]}


class _IAM__In_Memory(IAM__AWS__Client):
    def __init__(self):
        super().__init__()
        self._fake = _Fake_IAM_Boto()

    def client(self):
        return self._fake

    def setup(self):
        return self


# ── helpers ───────────────────────────────────────────────────────────────────

def _iam_setup() -> tuple:
    fake = _IAM__In_Memory()
    svc  = Setup__IAM(_iam_client_factory=lambda: fake)
    return svc, fake


# ── check: role absent ────────────────────────────────────────────────────────

class TestSetupIAMCheck_RoleAbsent:
    def test_state_is_missing(self):
        svc, _ = _iam_setup()
        assert svc.check().state == Enum__Setup__State.MISSING

    def test_role_name_correct(self):
        svc, _ = _iam_setup()
        assert svc.check().role_name == WAKER_ROLE_NAME

    def test_role_exists_false(self):
        svc, _ = _iam_setup()
        assert svc.check().role_exists is False

    def test_issues_not_empty(self):
        svc, _ = _iam_setup()
        assert len(list(svc.check().issues)) > 0

    def test_issue_severity_error(self):
        svc, _ = _iam_setup()
        assert list(svc.check().issues)[0].severity == 'error'


# ── check: role present, policy correct ───────────────────────────────────────

class TestSetupIAMCheck_RoleOK:
    def _with_role(self):
        svc, fake = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        return svc, fake

    def test_state_is_ok(self):
        svc, _ = self._with_role()
        assert svc.check().state == Enum__Setup__State.OK

    def test_role_exists_true(self):
        svc, _ = self._with_role()
        assert svc.check().role_exists is True

    def test_policy_matches_true(self):
        svc, _ = self._with_role()
        assert svc.check().policy_matches is True

    def test_no_issues(self):
        svc, _ = self._with_role()
        assert len(list(svc.check().issues)) == 0

    def test_role_arn_contains_role_name(self):
        svc, _ = self._with_role()
        assert WAKER_ROLE_NAME in svc.check().role_arn


# ── check: role present, policy drifted ───────────────────────────────────────

class TestSetupIAMCheck_PolicyDrift:
    def _with_drifted_policy(self):
        svc, fake = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        drifted_doc = json.dumps({
            'Version'  : '2012-10-17',
            'Statement': [{'Effect': 'Allow', 'Action': ['ec2:DescribeInstances'], 'Resource': ['*']}],
        })
        fake._fake.put_role_policy(WAKER_ROLE_NAME, WAKER_POLICY_NAME, drifted_doc)
        return svc, fake

    def test_state_is_drift(self):
        svc, _ = self._with_drifted_policy()
        assert svc.check().state == Enum__Setup__State.DRIFT

    def test_missing_actions_not_empty(self):
        svc, _ = self._with_drifted_policy()
        assert svc.check().missing_actions != ''

    def test_has_issues(self):
        svc, _ = self._with_drifted_policy()
        assert len(list(svc.check().issues)) > 0


# ── create ────────────────────────────────────────────────────────────────────

class TestSetupIAMCreate:
    def test_create_requires_mutation_gate(self):
        svc, _ = _iam_setup()
        env_bak = os.environ.pop('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS', None)
        try:
            with pytest.raises(RuntimeError, match='ALLOW_MUTATIONS'):
                svc.create()
        finally:
            if env_bak is not None:
                os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = env_bak

    def test_create_role_exists_after(self):
        svc, fake = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        assert WAKER_ROLE_NAME in fake._fake._roles

    def test_create_inline_policy_attached(self):
        svc, fake = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        assert WAKER_POLICY_NAME in fake._fake._inline_policies.get(WAKER_ROLE_NAME, {})

    def test_create_returns_ok_state(self):
        svc, _ = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        rep = svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        assert rep.state == Enum__Setup__State.OK

    def test_create_idempotent(self):
        svc, _ = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        rep = svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        assert rep.state == Enum__Setup__State.OK


# ── update ────────────────────────────────────────────────────────────────────

class TestSetupIAMUpdate:
    def test_update_syncs_policy(self):
        svc, fake = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        fake._fake.put_role_policy(WAKER_ROLE_NAME, WAKER_POLICY_NAME,
                                   json.dumps({'Version': '2012-10-17', 'Statement': []}))
        rep = svc.update()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        assert rep.state == Enum__Setup__State.OK

    def test_update_requires_mutation_gate(self):
        svc, _ = _iam_setup()
        env_bak = os.environ.pop('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS', None)
        try:
            with pytest.raises(RuntimeError, match='ALLOW_MUTATIONS'):
                svc.update()
        finally:
            if env_bak is not None:
                os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = env_bak


# ── delete ────────────────────────────────────────────────────────────────────

class TestSetupIAMDelete:
    def test_delete_requires_delete_gate(self):
        svc, _ = _iam_setup()
        env_bak = os.environ.pop('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES', None)
        try:
            with pytest.raises(RuntimeError, match='ALLOW_DELETES'):
                svc.delete()
        finally:
            if env_bak is not None:
                os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'] = env_bak

    def test_delete_removes_role(self):
        svc, fake = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'] = '1'
        svc.delete()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES']
        assert WAKER_ROLE_NAME not in fake._fake._roles

    def test_delete_when_absent_returns_missing(self):
        svc, _ = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'] = '1'
        rep = svc.delete()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES']
        assert rep.state == Enum__Setup__State.MISSING


# ── status ────────────────────────────────────────────────────────────────────

class TestSetupIAMStatus:
    def test_status_when_absent(self):
        svc, _ = _iam_setup()
        info = svc.status()
        assert info['exists'] is False

    def test_status_when_present(self):
        svc, _ = _iam_setup()
        os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'] = '1'
        svc.create()
        del os.environ['SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS']
        info = svc.status()
        assert info['exists'] is True
        assert info['role'] == WAKER_ROLE_NAME
