# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__Launch__Helper
# Calls ec2.run_instances for a Docker node.
# AL2023 always uses /dev/xvda as the root device on x86_64 — when disk_size_gb
# is > 0 we override the AMI's default block-device mapping with a gp3 volume
# of the requested size. Zero means: keep the AMI default.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from typing                                                                         import List, Optional

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


AL2023_ROOT_DEVICE_NAME = '/dev/xvda'


class Docker__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def build_run_instances_kwargs(self, ami_id                : str           ,
                                         security_group_id     : str           ,
                                         user_data             : str           ,
                                         tags                  : List[dict]    ,
                                         instance_type         : str           = 't3.medium' ,
                                         instance_profile_name : Optional[str] = None        ,
                                         disk_size_gb          : int           = 0           ) -> dict:
        kwargs = dict(ImageId           = ami_id                                                          ,
                      InstanceType      = instance_type                                                   ,
                      MinCount          = 1                                                               ,
                      MaxCount          = 1                                                               ,
                      SecurityGroupIds  = [security_group_id]                                             ,
                      UserData          = base64.b64encode(user_data.encode('utf-8')).decode('ascii')     ,
                      TagSpecifications = [{'ResourceType': 'instance', 'Tags': tags}]                    )
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        if disk_size_gb and disk_size_gb > 0:
            kwargs['BlockDeviceMappings'] = [{
                'DeviceName' : AL2023_ROOT_DEVICE_NAME           ,
                'Ebs'        : {'VolumeSize'         : int(disk_size_gb),
                                'VolumeType'         : 'gp3'            ,
                                'DeleteOnTermination': True             }
            }]
        return kwargs

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = 't3.medium'          ,
                           instance_profile_name : Optional[str] = None              ,
                           disk_size_gb          : int        = 0                    ) -> str:
        kwargs    = self.build_run_instances_kwargs(ami_id                = ami_id                ,
                                                     security_group_id     = security_group_id    ,
                                                     user_data             = user_data            ,
                                                     tags                  = tags                 ,
                                                     instance_type         = instance_type        ,
                                                     instance_profile_name = instance_profile_name,
                                                     disk_size_gb          = disk_size_gb         )
        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
