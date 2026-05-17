# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__IAM__Helper
# Ensures the EC2 instance profile for Firefox stacks exists.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


INSTANCE_PROFILE_NAME  = 'sg-firefox-ec2'
SSM_MANAGED_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
EC2_TRUST_POLICY = {'Version'  : '2012-10-17',
                    'Statement': [{'Effect'   : 'Allow'                        ,
                                   'Principal': {'Service': 'ec2.amazonaws.com'},
                                   'Action'   : 'sts:AssumeRole'               }]}


class Firefox__IAM__Helper(Type_Safe):

    def iam_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='iam', region=region or '')

    def ensure(self, region: str) -> str:
        iam       = self.iam_client(region)
        name      = INSTANCE_PROFILE_NAME
        not_found = iam.exceptions.NoSuchEntityException
        try:
            iam.get_role(RoleName=name)
        except not_found:
            iam.create_role(RoleName                 = name                        ,
                            AssumeRolePolicyDocument = json.dumps(EC2_TRUST_POLICY),
                            Description              = 'SG Firefox EC2 instance role')
        try:
            iam.attach_role_policy(RoleName=name, PolicyArn=SSM_MANAGED_POLICY_ARN)
        except Exception:
            pass
        try:
            iam.get_instance_profile(InstanceProfileName=name)
        except not_found:
            iam.create_instance_profile(InstanceProfileName=name)
            iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=name)
        return name
