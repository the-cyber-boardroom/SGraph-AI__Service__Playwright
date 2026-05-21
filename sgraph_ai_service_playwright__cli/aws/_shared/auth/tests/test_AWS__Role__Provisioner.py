# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — aws shared auth: AWS__Role__Provisioner
# No AWS: a real in-memory IAM__AWS__Client subclass holds roles in a dict. Covers the
# plan diff (empty → add all; in-sync after apply), idempotent apply, and delete.
# Fake__IAM is reused by the Cli__CF__Iam tests.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.auth                            import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Role__Provisioner     import AWS__Role__Provisioner
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client            import IAM__AWS__Client
from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Policy import List__Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role           import Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Response import Schema__IAM__Role__Create__Response
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn  import Safe_Str__IAM__Role_Arn


class Fake__IAM(IAM__AWS__Client):                                                   # in-memory; no boto3, no client() seam used
    roles : dict                                                                     # role_name → Schema__IAM__Role

    def get_role(self, role_name):
        return self.roles.get(role_name)

    def create_role_with_trust(self, role_name, trust_json, description=''):
        created = role_name not in self.roles
        if created:
            self.roles[role_name] = Schema__IAM__Role(
                role_name = Safe_Str__IAM__Role_Name(role_name),
                role_arn  = Safe_Str__IAM__Role_Arn(f'arn:aws:iam::123456789012:role/{role_name}'))
        return Schema__IAM__Role__Create__Response(
            role_name = Safe_Str__IAM__Role_Name(role_name),
            role_arn  = self.roles[role_name].role_arn,
            created   = created,
            message   = 'created' if created else 'already exists')

    def update_assume_role_policy_raw(self, role_name, trust_json):
        return role_name in self.roles

    def put_raw_inline_policy(self, role_name, policy_name, policy_json):
        role        = self.roles[role_name]
        policy      = self._parse_policy_doc(json.loads(policy_json))                # inherited pure parser
        policy.name = policy_name
        role.inline_policies = List__Schema__IAM__Policy()
        role.inline_policies.append(policy)
        return True

    def delete_role(self, role_name):
        return self.roles.pop(role_name, None) is not None


class test_AWS__Role__Provisioner(TestCase):

    def setUp(self):
        self.profile = profiles.get_profile('el-lets-cf')
        self.prov    = AWS__Role__Provisioner(iam=Fake__IAM(), account_id='123456789012')

    def test_plan_when_absent_adds_all(self):
        plan = self.prov.plan(self.profile)
        assert plan.exists  is False
        assert plan.in_sync is False
        assert 's3:GetObject' in plan.actions_to_add
        assert plan.actions_current == []
        assert plan.role_arn == 'arn:aws:iam::123456789012:role/sg-lets-cf'

    def test_apply_then_in_sync(self):
        resp = self.prov.apply(self.profile)
        assert resp.created is True
        plan = self.prov.plan(self.profile)
        assert plan.exists  is True
        assert plan.in_sync is True
        assert plan.actions_to_add    == []
        assert plan.actions_to_remove == []

    def test_apply_is_idempotent(self):
        self.prov.apply(self.profile)
        resp2 = self.prov.apply(self.profile)
        assert resp2.created is False                                                # role already exists on 2nd apply
        assert self.prov.plan(self.profile).in_sync is True

    def test_delete(self):
        self.prov.apply(self.profile)
        assert self.prov.delete(self.profile) is True
        assert self.prov.plan(self.profile).exists is False
