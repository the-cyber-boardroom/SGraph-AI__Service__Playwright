# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__IAM__Helper
# Idempotent IAM bootstrap for the firefox EC2 plugin.
#
# One role + one instance profile, both named PROFILE_NAME:
#   - Assume-role trust: ec2.amazonaws.com only
#   - Attached policy: AmazonSSMManagedInstanceCore
#     (required for SSM agent: sp firefox connect, set-interceptor)
#
# Every method is safe to call multiple times — it no-ops when the resource
# already exists. Call ensure() once per account/region before first create.
# IAM is global; region param is ignored but kept for symmetry with other helpers.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


PROFILE_NAME           = 'playwright-ec2'
SSM_POLICY_ARN         = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
IAM_ROLE_DESCRIPTION   = 'SG ephemeral firefox - SSM agent access'                 # ASCII only; IAM rejects multi-byte unicode in Description

EC2_TRUST_POLICY = {
    'Version'  : '2012-10-17',
    'Statement': [{'Effect'   : 'Allow'                         ,
                   'Principal': {'Service': 'ec2.amazonaws.com'},
                   'Action'   : 'sts:AssumeRole'                }]
}


class Firefox__IAM__Helper(Type_Safe):

    def iam_client(self, region: str):                                              # IAM is global; region kept for call symmetry
        return boto3.client('iam', region_name=region)

    def ensure(self, region: str) -> str:                                           # Idempotent; returns PROFILE_NAME
        iam       = self.iam_client(region)
        name      = PROFILE_NAME
        not_found = iam.exceptions.NoSuchEntityException

        try:                                                                        # 1) IAM role
            iam.get_role(RoleName=name)
        except not_found:
            iam.create_role(RoleName                  = name                        ,
                            AssumeRolePolicyDocument  = json.dumps(EC2_TRUST_POLICY),
                            Description               = IAM_ROLE_DESCRIPTION        )

        try:                                                                        # 2) SSM policy (AWS no-ops if already attached)
            iam.attach_role_policy(RoleName=name, PolicyArn=SSM_POLICY_ARN)
        except Exception:
            pass

        try:                                                                        # 3) Instance profile
            iam.get_instance_profile(InstanceProfileName=name)
        except not_found:
            iam.create_instance_profile(InstanceProfileName=name)

        self._link_role_to_profile(iam, name)                                       # 4) Attach role to profile (retries for IAM propagation delay)
        return name

    def _link_role_to_profile(self, iam, name: str) -> None:                       # Idempotent; retries up to 4x for IAM eventual consistency
        for attempt in range(4):
            try:
                profile = iam.get_instance_profile(InstanceProfileName=name)
                roles   = profile.get('InstanceProfile', {}).get('Roles', [])
                if any(r.get('RoleName') == name for r in roles):
                    return
                iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=name)
                return
            except iam.exceptions.NoSuchEntityException:                            # Not visible yet after create — back off and retry
                if attempt == 3:
                    raise
                time.sleep(5)
            except iam.exceptions.LimitExceededException:                           # Profile already has a different role — needs manual intervention
                raise

    def status(self, region: str) -> dict:                                          # Returns presence info; used by `sp firefox setup --check`
        iam       = self.iam_client(region)
        name      = PROFILE_NAME
        not_found = iam.exceptions.NoSuchEntityException
        role_ok   = profile_ok = policy_ok = False
        try:
            iam.get_role(RoleName=name)
            role_ok = True
        except not_found:
            pass
        try:
            resp       = iam.get_instance_profile(InstanceProfileName=name)
            profile_ok = True
            roles      = resp.get('InstanceProfile', {}).get('Roles', [])
            policy_ok  = any(r.get('RoleName') == name for r in roles)
        except not_found:
            pass
        return {'profile_name': name    ,
                'role'        : role_ok ,
                'profile'     : profile_ok,
                'role_linked' : policy_ok  }
