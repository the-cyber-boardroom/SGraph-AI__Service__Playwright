# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — IAM__AWS__Client__In_Memory
# Dict-backed fake boto3 IAM client for unit tests. No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client import IAM__AWS__Client


class _Fake_IAM_Client:
    """Minimal boto3-alike IAM client backed by in-memory dicts."""

    def __init__(self, roles: dict, inline_policies: dict, managed_attachments: dict):
        self._roles              = roles               # role_name → role_dict
        self._inline_policies    = inline_policies     # role_name → {policy_name: doc}
        self._managed_attachments= managed_attachments # role_name → [policy_arn, ...]

    # ── paginator ─────────────────────────────────────────────────────────────

    def get_paginator(self, method: str):
        return _Fake_Paginator(self, method)

    # ── role CRUD ─────────────────────────────────────────────────────────────

    def get_role(self, RoleName: str):
        if RoleName not in self._roles:
            raise Exception(f'NoSuchEntity: {RoleName}')
        return {'Role': self._roles[RoleName]}

    def create_role(self, RoleName: str, AssumeRolePolicyDocument: str, Description: str = '', **_):
        if RoleName in self._roles:
            raise Exception('EntityAlreadyExists')
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
            raise Exception(f'NoSuchEntity: {RoleName}')
        del self._roles[RoleName]
        self._inline_policies.pop(RoleName, None)
        self._managed_attachments.pop(RoleName, None)

    # ── inline policies ───────────────────────────────────────────────────────

    def put_role_policy(self, RoleName: str, PolicyName: str, PolicyDocument: str, **_):
        if RoleName not in self._roles:
            raise Exception(f'NoSuchEntity: {RoleName}')
        if RoleName not in self._inline_policies:
            self._inline_policies[RoleName] = {}
        self._inline_policies[RoleName][PolicyName] = json.loads(PolicyDocument)

    def get_role_policy(self, RoleName: str, PolicyName: str, **_):
        if RoleName not in self._inline_policies or PolicyName not in self._inline_policies[RoleName]:
            raise Exception(f'NoSuchEntity: {PolicyName}')
        return {
            'RoleName'      : RoleName,
            'PolicyName'    : PolicyName,
            'PolicyDocument': self._inline_policies[RoleName][PolicyName],
        }

    def delete_role_policy(self, RoleName: str, PolicyName: str, **_):
        if RoleName in self._inline_policies:
            self._inline_policies[RoleName].pop(PolicyName, None)

    # ── managed policy attachments ────────────────────────────────────────────

    def attach_role_policy(self, RoleName: str, PolicyArn: str, **_):
        if RoleName not in self._roles:
            raise Exception(f'NoSuchEntity: {RoleName}')
        if RoleName not in self._managed_attachments:
            self._managed_attachments[RoleName] = []
        if PolicyArn not in self._managed_attachments[RoleName]:
            self._managed_attachments[RoleName].append(PolicyArn)

    def detach_role_policy(self, RoleName: str, PolicyArn: str, **_):
        if RoleName in self._managed_attachments:
            self._managed_attachments[RoleName] = [
                a for a in self._managed_attachments[RoleName] if a != PolicyArn
            ]


class _Fake_Paginator:
    def __init__(self, client: _Fake_IAM_Client, method: str):
        self._client = client
        self._method = method

    def paginate(self, **kwargs):
        if self._method == 'list_roles':
            yield {'Roles': list(self._client._roles.values())}
        elif self._method == 'list_role_policies':
            role = kwargs.get('RoleName', '')
            names = list(self._client._inline_policies.get(role, {}).keys())
            yield {'PolicyNames': names}
        elif self._method == 'list_attached_role_policies':
            role = kwargs.get('RoleName', '')
            arns = self._client._managed_attachments.get(role, [])
            yield {'AttachedPolicies': [{'PolicyArn': a, 'PolicyName': a.split('/')[-1]} for a in arns]}


class IAM__AWS__Client__In_Memory(IAM__AWS__Client):

    def __init__(self):
        super().__init__()
        self._roles               = {}
        self._inline_policies     = {}
        self._managed_attachments = {}
        self._fake = _Fake_IAM_Client(self._roles, self._inline_policies, self._managed_attachments)

    def client(self):
        return self._fake
