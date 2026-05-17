# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__Launch__Helper
# Launches EC2 instances for Firefox stacks.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Firefox__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def run_instance(self, region: str, ami_id: str, sg_id: str, user_data: str,
                           tags: List[dict], instance_type: str = 't3.medium',
                           instance_profile_name: str = '', max_hours: int = 1) -> str:
        ec2    = self.ec2_client(region)
        kwargs = dict(ImageId          = ami_id                                    ,
                      InstanceType     = instance_type                             ,
                      MinCount         = 1                                         ,
                      MaxCount         = 1                                         ,
                      SecurityGroupIds = [sg_id]                                   ,
                      UserData         = user_data                                 ,
                      TagSpecifications= [{'ResourceType': 'instance', 'Tags': tags}])
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        if max_hours > 0:
            kwargs['InstanceInitiatedShutdownBehavior'] = 'terminate'
        for attempt in range(3):
            try:
                result = ec2.run_instances(**kwargs)
                break
            except Exception as exc:
                msg = str(exc)
                if attempt < 2 and 'InvalidParameterValue' in msg and 'instance profile' in msg.lower():
                    time.sleep(5)
                    continue
                raise
        instances = result.get('Instances', [])
        return str(instances[0].get('InstanceId', '')) if instances else ''
