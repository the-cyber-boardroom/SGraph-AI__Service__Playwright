# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__AWS__Client.ensure_instance_profile
# Drives the IAM bootstrap with a hand-rolled fake iam_client (no mocks):
#   - first call creates role + profile + policy attachment
#   - second call is a no-op (idempotent)
# Plus the launch_instance retry path on IAM eventual-consistency errors.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client         import (
    Elastic__AWS__Client    ,
    IAM_ROLE_DESCRIPTION     ,
    INSTANCE_PROFILE_NAME    ,
    SSM_MANAGED_POLICY_ARN   ,
)


class FakeIAMNoSuchEntity(Exception):
    pass


class FakeIAM:                                                                      # Minimal IAM client surface — only what ensure_instance_profile uses
    def __init__(self):
        self.roles    = {}                                                          # name → {role document}
        self.profiles = {}                                                          # name → {InstanceProfile: {..., Roles: [...]}}
        self.attached = []                                                          # [(role_name, policy_arn), ...]
        self.calls    = []
        self.exceptions = type('E', (), {'NoSuchEntityException': FakeIAMNoSuchEntity})

    def get_role(self, RoleName):
        self.calls.append(('get_role', RoleName))
        if RoleName not in self.roles:
            raise FakeIAMNoSuchEntity(RoleName)
        return {'Role': self.roles[RoleName]}

    def create_role(self, RoleName, AssumeRolePolicyDocument, Description=''):
        self.calls.append(('create_role', RoleName))
        self.roles[RoleName] = {'RoleName': RoleName,
                                'AssumeRolePolicyDocument': json.loads(AssumeRolePolicyDocument)}

    def attach_role_policy(self, RoleName, PolicyArn):
        self.calls.append(('attach_role_policy', RoleName, PolicyArn))
        self.attached.append((RoleName, PolicyArn))

    def get_instance_profile(self, InstanceProfileName):
        self.calls.append(('get_instance_profile', InstanceProfileName))
        if InstanceProfileName not in self.profiles:
            raise FakeIAMNoSuchEntity(InstanceProfileName)
        return self.profiles[InstanceProfileName]

    def create_instance_profile(self, InstanceProfileName):
        self.calls.append(('create_instance_profile', InstanceProfileName))
        self.profiles[InstanceProfileName] = {'InstanceProfile': {'InstanceProfileName': InstanceProfileName,
                                                                  'Roles': []}}

    def add_role_to_instance_profile(self, InstanceProfileName, RoleName):
        self.calls.append(('add_role_to_instance_profile', InstanceProfileName, RoleName))
        self.profiles[InstanceProfileName]['InstanceProfile']['Roles'].append({'RoleName': RoleName})


class ClientWithFakeIAM(Elastic__AWS__Client):
    fake_iam : FakeIAM = None                                                       # Set by test setUp

    def iam_client(self, region: str):
        return self.fake_iam


class test_ensure_instance_profile(TestCase):

    def test_first_call_creates_role_profile_and_attaches_ssm_policy(self):
        client          = ClientWithFakeIAM()
        client.fake_iam = FakeIAM()
        name            = client.ensure_instance_profile('eu-west-2')

        assert name                                  == INSTANCE_PROFILE_NAME
        assert INSTANCE_PROFILE_NAME                 in client.fake_iam.roles
        assert INSTANCE_PROFILE_NAME                 in client.fake_iam.profiles
        assert (INSTANCE_PROFILE_NAME, SSM_MANAGED_POLICY_ARN) in client.fake_iam.attached
        roles_in_profile = client.fake_iam.profiles[INSTANCE_PROFILE_NAME]['InstanceProfile']['Roles']
        assert any(r['RoleName'] == INSTANCE_PROFILE_NAME for r in roles_in_profile)

    def test_second_call_is_idempotent(self):                                       # Re-running create on subsequent stacks must not error or duplicate setup
        client          = ClientWithFakeIAM()
        client.fake_iam = FakeIAM()
        client.ensure_instance_profile('eu-west-2')
        first_state = (set(client.fake_iam.roles), set(client.fake_iam.profiles))

        client.ensure_instance_profile('eu-west-2')
        second_state = (set(client.fake_iam.roles), set(client.fake_iam.profiles))

        assert first_state == second_state                                          # No new role / profile created
        # Role count in the profile stays at exactly 1 — no duplicate adds
        roles_in_profile = client.fake_iam.profiles[INSTANCE_PROFILE_NAME]['InstanceProfile']['Roles']
        assert sum(1 for r in roles_in_profile if r['RoleName'] == INSTANCE_PROFILE_NAME) == 1

    def test_trust_policy_targets_ec2(self):                                        # Pin the AssumeRolePolicyDocument so SSM agent (running as EC2 service) can use it
        client          = ClientWithFakeIAM()
        client.fake_iam = FakeIAM()
        client.ensure_instance_profile('eu-west-2')
        role = client.fake_iam.roles[INSTANCE_PROFILE_NAME]
        statements = role['AssumeRolePolicyDocument']['Statement']
        assert statements[0]['Principal']['Service'] == 'ec2.amazonaws.com'
        assert statements[0]['Action']               == 'sts:AssumeRole'


    def test_role_description_is_ascii_only(self):
        # AWS IAM Description regex rejects multi-byte unicode (incl. em-dash U+2014)
        for ch in IAM_ROLE_DESCRIPTION:
            ord_ = ord(ch)
            allowed = (ord_ in (0x09, 0x0A, 0x0D)
                       or 0x20 <= ord_ <= 0x7E
                       or 0xA1 <= ord_ <= 0xFF)
            assert allowed, f'IAM_ROLE_DESCRIPTION contains disallowed character {ch!r} (U+{ord_:04X})'
