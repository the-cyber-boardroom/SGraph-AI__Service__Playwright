# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__Launch__Helper
# Single responsibility: calls boto3 ec2.run_instances for a Playwright stack.
# Mirrors Vnc__Launch__Helper. Default instance type sized for playwright +
# host-control container. InstanceInitiatedShutdownBehavior=terminate ensures
# the auto-terminate timer (Section__Shutdown) causes termination not stop.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from typing                                                                      import List, Optional

import boto3                                                                     # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


DEFAULT_INSTANCE_TYPE = 't3.medium'                                              # 2 vCPU / 4 GB — adequate for playwright + host-control


class Playwright__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):                                           # Single seam — tests override
        return boto3.client('ec2', region_name=region)

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = DEFAULT_INSTANCE_TYPE,
                           instance_profile_name : Optional[str] = None          ,
                           max_hours             : int           = 1             ) -> str:
        kwargs = dict(ImageId                              = ami_id                                                                ,
                      InstanceType                         = instance_type                                                         ,
                      MinCount                             = 1                                                                     ,
                      MaxCount                             = 1                                                                     ,
                      SecurityGroupIds                     = [security_group_id]                                                   ,
                      UserData                             = base64.b64encode(user_data.encode('utf-8')).decode('ascii')           ,
                      TagSpecifications                    = [{'ResourceType': 'instance', 'Tags': tags}]                          ,
                      InstanceInitiatedShutdownBehavior    = 'terminate'         )                                                 # Paired with Section__Shutdown systemd-run — halt causes termination
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}

        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
