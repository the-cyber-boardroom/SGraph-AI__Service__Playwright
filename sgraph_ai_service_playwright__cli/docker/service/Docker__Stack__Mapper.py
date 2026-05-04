# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__Stack__Mapper
# Pure mapper from raw boto3 describe_instances detail dict → Schema__Docker__Info.
# Mirrors Linux__Stack__Mapper. No AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.docker.enums.Enum__Docker__Stack__State      import Enum__Docker__Stack__State
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Info          import Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.service.Docker__AWS__Client           import (TAG_ALLOWED_IP_KEY ,
                                                                                              TAG_STACK_NAME_KEY )


def _tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _state_str(details: dict) -> str:
    state_raw = details.get('State', {})
    return state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)


def _state_to_enum(state_str: str) -> Enum__Docker__Stack__State:
    mapping = {'pending'      : Enum__Docker__Stack__State.PENDING    ,
               'running'      : Enum__Docker__Stack__State.RUNNING    ,
               'shutting-down': Enum__Docker__Stack__State.TERMINATING,
               'stopping'     : Enum__Docker__Stack__State.STOPPING   ,
               'stopped'      : Enum__Docker__Stack__State.STOPPED    ,
               'terminated'   : Enum__Docker__Stack__State.TERMINATED }
    return mapping.get(state_str, Enum__Docker__Stack__State.UNKNOWN)


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


class Docker__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Docker__Info:
        return Schema__Docker__Info(
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
            spot              = details.get('InstanceLifecycle', '') == 'spot'                        ,
            launch_time       = str(details.get('LaunchTime', ''))                                   ,
            uptime_seconds    = _uptime_seconds(details)                                             )
