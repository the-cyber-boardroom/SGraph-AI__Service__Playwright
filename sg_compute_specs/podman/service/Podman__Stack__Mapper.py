# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Podman__Stack__Mapper
# Pure mapper from raw boto3 describe_instances detail dict → Schema__Podman__Info.
# No AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.podman.enums.Enum__Podman__Stack__State                       import Enum__Podman__Stack__State
from sg_compute_specs.podman.schemas.Schema__Podman__Info                           import Schema__Podman__Info
from sg_compute_specs.podman.service.Podman__AWS__Client                            import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY


def _tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _state_str(details: dict) -> str:
    state_raw = details.get('State', {})
    return state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)


def _state_to_enum(state_str: str) -> Enum__Podman__Stack__State:
    mapping = {'pending'      : Enum__Podman__Stack__State.PENDING    ,
               'running'      : Enum__Podman__Stack__State.RUNNING    ,
               'shutting-down': Enum__Podman__Stack__State.TERMINATING,
               'stopping'     : Enum__Podman__Stack__State.STOPPING   ,
               'stopped'      : Enum__Podman__Stack__State.STOPPED    ,
               'terminated'   : Enum__Podman__Stack__State.TERMINATED }
    return mapping.get(state_str, Enum__Podman__Stack__State.UNKNOWN)


def _uptime_seconds(details: dict) -> int:
    launch_time = details.get('LaunchTime')
    if not launch_time:
        return 0
    try:
        import datetime
        if hasattr(launch_time, 'timestamp'):
            return int(time.time() - launch_time.timestamp())
        dt = datetime.datetime.fromisoformat(str(launch_time).replace('Z', '+00:00'))
        return int(time.time() - dt.timestamp())
    except Exception:
        return 0


class Podman__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Podman__Info:
        return Schema__Podman__Info(
            stack_name        = _tag(details, TAG_STACK_NAME_KEY)                                    ,
            aws_name_tag      = _tag(details, 'Name')                                                ,
            instance_id       = details.get('InstanceId', '')                                        ,
            region            = region                                                               ,
            ami_id            = details.get('ImageId', '')                                           ,
            instance_type     = details.get('InstanceType', '')                                      ,
            security_group_id = (details.get('SecurityGroups', [{}])[0].get('GroupId', '')
                                 if details.get('SecurityGroups') else '')                            ,
            allowed_ip        = _tag(details, TAG_ALLOWED_IP_KEY)                                    ,
            public_ip         = details.get('PublicIpAddress', '') or ''                             ,
            state             = _state_to_enum(_state_str(details))                                  ,
            launch_time       = str(details.get('LaunchTime', ''))                                   ,
            uptime_seconds    = _uptime_seconds(details)                                             )
