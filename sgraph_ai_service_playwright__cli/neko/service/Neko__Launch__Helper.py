# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Neko__Launch__Helper
# Runs an EC2 instance for a Neko stack. Mirrors VNC launch helper.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from typing                                                                         import List, Optional

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_INSTANCE_TYPE = 't3.large'                                                  # 2 vCPU / 8 GB — Neko + Chrome needs RAM headroom


class Neko__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = DEFAULT_INSTANCE_TYPE,
                           instance_profile_name : Optional[str] = None             ,
                           use_spot              : bool       = True                ) -> str:
        kwargs = dict(ImageId          = ami_id                                                           ,
                      InstanceType     = instance_type                                                    ,
                      MinCount         = 1                                                                 ,
                      MaxCount         = 1                                                                 ,
                      SecurityGroupIds = [security_group_id]                                               ,
                      UserData         = base64.b64encode(user_data.encode('utf-8')).decode('ascii')       ,
                      TagSpecifications= [{'ResourceType': 'instance', 'Tags': tags}]                      )
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        if use_spot:
            kwargs['InstanceMarketOptions'] = {'MarketType': 'spot'}
        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
