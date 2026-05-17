# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__Launch__Helper
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional
import base64

from typing                                                                         import List, Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_INSTANCE_TYPE = 't3.large'


class Neko__Launch__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def run_instance(self, region                : str        ,
                           ami_id                : str        ,
                           security_group_id     : str        ,
                           user_data             : str        ,
                           tags                  : List[dict] ,
                           instance_type         : str        = DEFAULT_INSTANCE_TYPE,
                           instance_profile_name : Optional[str] = None) -> str:
        kwargs = dict(ImageId          = ami_id                                                           ,
                      InstanceType     = instance_type                                                    ,
                      MinCount         = 1                                                                 ,
                      MaxCount         = 1                                                                 ,
                      SecurityGroupIds = [security_group_id]                                               ,
                      UserData         = base64.b64encode(user_data.encode('utf-8')).decode('ascii')       ,
                      TagSpecifications= [{'ResourceType': 'instance', 'Tags': tags}]                      )
        if instance_profile_name:
            kwargs['IamInstanceProfile'] = {'Name': instance_profile_name}
        resp      = self.ec2_client(region).run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            raise RuntimeError('run_instances returned no Instances')
        return instances[0].get('InstanceId', '')
