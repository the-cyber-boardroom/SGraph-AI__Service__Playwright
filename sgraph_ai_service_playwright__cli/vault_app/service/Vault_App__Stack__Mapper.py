# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__Stack__Mapper
# Converts a raw EC2 instance dict (from boto3 / osbot-aws) into a typed
# Schema__Vault_App__Stack__Info. Pure transformation; no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vault_app.enums.Enum__Vault_App__Stack__State  import Enum__Vault_App__Stack__State
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Info import Schema__Vault_App__Stack__Info
from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__AWS__Client     import TAG_STACK_NAME_KEY

EC2_STATE_MAP = {
    'pending'      : Enum__Vault_App__Stack__State.PENDING     ,
    'running'      : Enum__Vault_App__Stack__State.RUNNING     ,
    'shutting-down': Enum__Vault_App__Stack__State.TERMINATING ,
    'terminated'   : Enum__Vault_App__Stack__State.TERMINATED  ,
    'stopping'     : Enum__Vault_App__Stack__State.TERMINATING ,
    'stopped'      : Enum__Vault_App__Stack__State.TERMINATED  ,
}


def _tag(instance: dict, key: str) -> str:
    for t in (instance.get('Tags') or []):
        if t.get('Key') == key:
            return t.get('Value', '')
    return ''


class Vault_App__Stack__Mapper(Type_Safe):

    def instance_to_info(self, instance: dict) -> Optional[Schema__Vault_App__Stack__Info]:
        stack_name = _tag(instance, TAG_STACK_NAME_KEY)
        if not stack_name:
            return None
        public_ip  = instance.get('PublicIpAddress', '')
        ec2_state  = (instance.get('State') or {}).get('Name', '')
        return Schema__Vault_App__Stack__Info(
            stack_name        = stack_name                                         ,
            aws_name_tag      = _tag(instance, 'Name')                            ,
            instance_id       = instance.get('InstanceId', '')                    ,
            region            = ''                                                 ,                # caller sets from request context
            ami_id            = instance.get('ImageId', '')                       ,
            instance_type     = instance.get('InstanceType', '')                  ,
            security_group_id = (instance.get('SecurityGroups') or [{}])[0].get('GroupId', ''),
            public_ip         = public_ip                                          ,
            vault_url         = f'http://{public_ip}:8080/' if public_ip else ''  ,
            state             = EC2_STATE_MAP.get(ec2_state,
                                                  Enum__Vault_App__Stack__State.UNKNOWN),
            launch_time       = str(instance.get('LaunchTime', ''))               ,
        )
