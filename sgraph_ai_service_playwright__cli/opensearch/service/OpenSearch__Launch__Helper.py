# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__Launch__Helper
# Single responsibility: calls boto3 ec2.run_instances for an OpenSearch
# stack. Kept separate from OpenSearch__Instance__Helper (which is
# read-only + terminate) so the launch surface is reviewable in isolation.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from typing                                                                         import List, Optional

import boto3                                                                        # EXCEPTION — narrow boto3 boundary, see plan doc 2

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_INSTANCE_TYPE = 't3.large'                                                  # 2 vCPU / 8 GB — fits OS + Dashboards comfortably; cheaper than the elastic m6i.xlarge default


class OpenSearch__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        return boto3.client('ec2', region_name=region)

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = DEFAULT_INSTANCE_TYPE,
                           instance_profile_name : Optional[str] = None             ,
                           use_spot              : bool       = True                ) -> str:    # Returns the EC2 instance_id
        kwargs = dict(ImageId          = ami_id                                                            ,
                      InstanceType     = instance_type                                                     ,
                      MinCount         = 1                                                                  ,
                      MaxCount         = 1                                                                  ,
                      SecurityGroupIds = [security_group_id]                                                ,
                      UserData         = base64.b64encode(user_data.encode('utf-8')).decode('ascii')        ,   # AWS expects base64-encoded UserData
                      TagSpecifications= [{'ResourceType': 'instance', 'Tags': tags}]                       )
        if instance_profile_name:                                                   # Optional — sp os reuses the playwright-ec2 profile when this is unset
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        if use_spot:
            kwargs['InstanceMarketOptions'] = {'MarketType': 'spot'}

        resp = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
