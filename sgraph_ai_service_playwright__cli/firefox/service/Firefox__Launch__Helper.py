# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__Launch__Helper
# Runs an EC2 instance for a Firefox stack. Mirrors neko launch helper.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import gzip

from typing                                                                         import List, Optional

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_INSTANCE_TYPE = 't3.medium'                                                 # 2 vCPU / 4 GB — Firefox noVNC is lighter than Neko WebRTC


class Firefox__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = DEFAULT_INSTANCE_TYPE,
                           instance_profile_name : Optional[str] = None             ,
                           max_hours             : int        = 0                   ,
                           use_spot              : bool       = True                ) -> str:
        kwargs = dict(ImageId          = ami_id                                                                      ,
                      InstanceType     = instance_type                                                               ,
                      MinCount         = 1                                                                            ,
                      MaxCount         = 1                                                                            ,
                      SecurityGroupIds = [security_group_id]                                                          ,
                      UserData         = base64.b64encode(gzip.compress(user_data.encode('utf-8'))).decode('ascii')  ,  # gzip: cloud-init decompresses transparently; avoids 25600-byte encoded limit
                      TagSpecifications= [{'ResourceType': 'instance', 'Tags': tags}]                                )
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        if max_hours > 0:
            kwargs['InstanceInitiatedShutdownBehavior'] = 'terminate'               # paired with systemd-run shutdown timer in user-data
        if use_spot:
            kwargs['InstanceMarketOptions'] = {'MarketType': 'spot'}
        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
