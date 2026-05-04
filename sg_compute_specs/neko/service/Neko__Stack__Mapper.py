# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__Stack__Mapper
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.neko.enums.Enum__Neko__Stack__State                           import Enum__Neko__Stack__State
from sg_compute_specs.neko.schemas.Schema__Neko__Stack__Info                        import Schema__Neko__Stack__Info
from sg_compute_specs.neko.service.Neko__AWS__Client                                import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY


def _tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _state_to_enum(details: dict) -> Enum__Neko__Stack__State:
    raw = details.get('State', {})
    s   = raw.get('Name', '') if isinstance(raw, dict) else str(raw)
    return {'pending'      : Enum__Neko__Stack__State.PENDING    ,
            'running'      : Enum__Neko__Stack__State.RUNNING    ,
            'shutting-down': Enum__Neko__Stack__State.TERMINATING,
            'stopping'     : Enum__Neko__Stack__State.TERMINATING,
            'stopped'      : Enum__Neko__Stack__State.TERMINATED ,
            'terminated'   : Enum__Neko__Stack__State.TERMINATED }.get(s, Enum__Neko__Stack__State.UNKNOWN)


class Neko__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Neko__Stack__Info:
        ip = details.get('PublicIpAddress', '') or ''
        return Schema__Neko__Stack__Info(
            stack_name        = _tag(details, TAG_STACK_NAME_KEY)                                          ,
            aws_name_tag      = _tag(details, 'Name')                                                      ,
            instance_id       = details.get('InstanceId', '')                                              ,
            region            = region                                                                      ,
            ami_id            = details.get('ImageId', '')                                                  ,
            instance_type     = details.get('InstanceType', '')                                             ,
            security_group_id = (details.get('SecurityGroups', [{}])[0].get('GroupId', '')
                                 if details.get('SecurityGroups') else '')                                  ,
            allowed_ip        = _tag(details, TAG_ALLOWED_IP_KEY)                                          ,
            public_ip         = ip                                                                          ,
            viewer_url        = f'https://{ip}/' if ip else ''                                             ,
            state             = _state_to_enum(details)                                                    ,
            launch_time       = str(details.get('LaunchTime', ''))                                         )
