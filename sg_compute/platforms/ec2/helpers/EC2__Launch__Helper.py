# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — EC2__Launch__Helper
# Wraps RunInstances. Gzip+base64 encodes user-data (handles large scripts).
# When max_hours > 0 sets InstanceInitiatedShutdownBehavior=terminate so the
# systemd-run timer in user-data causes EC2 termination, not just halt.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import gzip
from typing                          import List

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe


AL2023_ROOT_DEVICE_NAME = '/dev/xvda'


class EC2__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def run_instance(self, region                : str       ,
                           ami_id                : str       ,
                           sg_id                 : str       ,
                           user_data             : str       ,
                           tags                  : List[dict],
                           instance_type         : str  = 't3.large'  ,
                           instance_profile      : str  = ''          ,
                           instance_profile_name : str  = ''          ,
                           max_hours             : int  = 0           ,
                           key_name              : str  = ''          ,
                           disk_size_gb          : int  = 0           ,
                           use_spot              : bool = False       ) -> str:
        encoded  = base64.b64encode(gzip.compress(user_data.encode('utf-8'))).decode('ascii')
        profile  = instance_profile_name or instance_profile
        kwargs   = dict(
            ImageId           = ami_id                                                          ,
            InstanceType      = instance_type                                                   ,
            MinCount          = 1                                                               ,
            MaxCount          = 1                                                               ,
            SecurityGroupIds  = [sg_id]                                                         ,
            UserData          = encoded                                                         ,
            TagSpecifications = [{'ResourceType': 'instance', 'Tags': tags}]                   ,
        )
        if profile:
            kwargs['IamInstanceProfile'] = {'Name': profile}
        if key_name:
            kwargs['KeyName'] = key_name
        if max_hours > 0 and not use_spot:                                                       # spot non-hibernation instances always terminate on OS shutdown; skip the flag (it's silently ignored)
            kwargs['InstanceInitiatedShutdownBehavior'] = 'terminate'
        if disk_size_gb and disk_size_gb > 0:
            kwargs['BlockDeviceMappings'] = [{
                'DeviceName': AL2023_ROOT_DEVICE_NAME,
                'Ebs'       : {'VolumeSize'         : int(disk_size_gb),
                               'VolumeType'         : 'gp3'            ,
                               'DeleteOnTermination': True             },
            }]
        if use_spot:
            kwargs['InstanceMarketOptions'] = {'MarketType': 'spot'}

        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('RunInstances returned no Instances')
        return instances[0].get('InstanceId', '')

    def add_tags(self, region: str, instance_id: str, tags: List[dict]) -> None:
        self.ec2_client(region).create_tags(Resources=[instance_id], Tags=tags)
