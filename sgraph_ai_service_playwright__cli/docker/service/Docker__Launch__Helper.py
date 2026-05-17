# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__Launch__Helper
# Calls ec2.run_instances for a Docker stack. Mirrors Linux__Launch__Helper.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from typing                                                                         import List, Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Docker__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    AL2023_ROOT_DEVICE_NAME = '/dev/xvda'

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = 't3.medium'          ,
                           instance_profile_name : Optional[str] = None             ,
                           use_spot              : bool       = True                ,
                           disk_size_gb          : int        = 0                   ) -> str:
        kwargs = dict(ImageId           = ami_id                                                           ,
                      InstanceType      = instance_type                                                    ,
                      MinCount          = 1                                                                 ,
                      MaxCount          = 1                                                                 ,
                      SecurityGroupIds  = [security_group_id]                                              ,
                      UserData          = base64.b64encode(user_data.encode('utf-8')).decode('ascii')       ,
                      TagSpecifications = [{'ResourceType': 'instance', 'Tags': tags}]                     )
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        if use_spot:
            kwargs['InstanceMarketOptions'] = {'MarketType': 'spot'}
        if disk_size_gb and disk_size_gb > 0:
            kwargs['BlockDeviceMappings'] = [{
                'DeviceName' : self.AL2023_ROOT_DEVICE_NAME    ,
                'Ebs'        : {'VolumeSize'         : int(disk_size_gb),
                                'VolumeType'         : 'gp3'            ,
                                'DeleteOnTermination': True             }
            }]

        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
