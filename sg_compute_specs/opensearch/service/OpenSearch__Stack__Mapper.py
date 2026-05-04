# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: OpenSearch__Stack__Mapper
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.opensearch.enums.Enum__OS__Stack__State                       import Enum__OS__Stack__State
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Info                    import Schema__OS__Stack__Info
from sg_compute_specs.opensearch.service.OpenSearch__AWS__Client                    import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY


def _tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _state_str(details: dict) -> str:
    state_raw = details.get('State', {})
    return state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)


def _state_to_enum(state_str: str) -> Enum__OS__Stack__State:
    mapping = {'pending'      : Enum__OS__Stack__State.PENDING    ,
               'running'      : Enum__OS__Stack__State.RUNNING    ,
               'shutting-down': Enum__OS__Stack__State.TERMINATING,
               'stopping'     : Enum__OS__Stack__State.TERMINATING,
               'stopped'      : Enum__OS__Stack__State.TERMINATED ,
               'terminated'   : Enum__OS__Stack__State.TERMINATED }
    return mapping.get(state_str, Enum__OS__Stack__State.UNKNOWN)


class OpenSearch__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__OS__Stack__Info:
        ip         = details.get('PublicIpAddress', '') or ''
        stack_name = _tag(details, TAG_STACK_NAME_KEY)
        return Schema__OS__Stack__Info(stack_name        = stack_name                                                           ,
                                       aws_name_tag      = _tag(details, 'Name')                                                ,
                                       instance_id       = details.get('InstanceId', '')                                        ,
                                       region            = region                                                               ,
                                       ami_id            = details.get('ImageId', '')                                           ,
                                       instance_type     = details.get('InstanceType', '')                                      ,
                                       security_group_id = (details.get('SecurityGroups', [{}])[0].get('GroupId', '')
                                                            if details.get('SecurityGroups') else '')                           ,
                                       allowed_ip        = _tag(details, TAG_ALLOWED_IP_KEY)                                    ,
                                       public_ip         = ip                                                                   ,
                                       dashboards_url    = f'https://{ip}/'      if ip else ''                                  ,
                                       os_endpoint       = f'https://{ip}:9200/' if ip else ''                                  ,
                                       state             = _state_to_enum(_state_str(details))                                  ,
                                       launch_time       = str(details.get('LaunchTime', ''))                                   )
