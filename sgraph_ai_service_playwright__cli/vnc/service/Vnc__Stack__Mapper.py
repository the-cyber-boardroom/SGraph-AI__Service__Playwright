# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__Stack__Mapper
# Pure mapper from raw boto3 describe_instances detail dict → Type_Safe
# Schema__Vnc__Stack__Info. No AWS calls, no network calls.
#
# Reads the `sg:interceptor` tag and decodes the N5 marker:
#   'none'                 → Enum__Vnc__Interceptor__Kind.NONE   + name=''
#   f'name:{example_name}' → Enum__Vnc__Interceptor__Kind.NAME   + name='{example_name}'
#   'inline'               → Enum__Vnc__Interceptor__Kind.INLINE + name='inline'
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import (TAG_ALLOWED_IP_KEY     ,
                                                                                              TAG_INTERCEPTOR_KEY    ,
                                                                                              TAG_INTERCEPTOR_NONE   ,
                                                                                              TAG_STACK_NAME_KEY     )


def _tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _state_str(details: dict) -> str:
    state_raw = details.get('State', {})
    return state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)


def _state_to_enum(state_str: str) -> Enum__Vnc__Stack__State:
    mapping = {'pending'      : Enum__Vnc__Stack__State.PENDING    ,
               'running'      : Enum__Vnc__Stack__State.RUNNING    ,
               'shutting-down': Enum__Vnc__Stack__State.TERMINATING,
               'stopping'     : Enum__Vnc__Stack__State.TERMINATING,
               'stopped'      : Enum__Vnc__Stack__State.TERMINATED ,
               'terminated'   : Enum__Vnc__Stack__State.TERMINATED }
    return mapping.get(state_str, Enum__Vnc__Stack__State.UNKNOWN)


def _interceptor_from_tag(raw: str):                                                # (kind, name) — decodes the N5 marker
    if raw == TAG_INTERCEPTOR_NONE or raw == '':
        return Enum__Vnc__Interceptor__Kind.NONE, ''
    if raw == 'inline':
        return Enum__Vnc__Interceptor__Kind.INLINE, 'inline'
    if raw.startswith('name:'):
        return Enum__Vnc__Interceptor__Kind.NAME, raw[len('name:'):]
    return Enum__Vnc__Interceptor__Kind.NONE, ''                                    # Defensive on unknown markers


class Vnc__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Vnc__Stack__Info:
        ip               = details.get('PublicIpAddress', '') or ''
        stack_name       = _tag(details, TAG_STACK_NAME_KEY)
        kind, label      = _interceptor_from_tag(_tag(details, TAG_INTERCEPTOR_KEY))
        return Schema__Vnc__Stack__Info(stack_name        = stack_name                                          ,
                                          aws_name_tag      = _tag(details, 'Name')                              ,
                                          instance_id       = details.get('InstanceId', '')                      ,
                                          region            = region                                             ,
                                          ami_id            = details.get('ImageId', '')                         ,
                                          instance_type     = details.get('InstanceType', '')                    ,
                                          security_group_id = (details.get('SecurityGroups', [{}])[0].get('GroupId', '')
                                                               if details.get('SecurityGroups') else '')         ,
                                          allowed_ip        = _tag(details, TAG_ALLOWED_IP_KEY)                  ,
                                          public_ip         = ip                                                 ,
                                          viewer_url        = f'https://{ip}/'           if ip else ''           ,
                                          mitmweb_url       = f'https://{ip}/mitmweb/'   if ip else ''           ,
                                          interceptor_kind  = kind                                                ,
                                          interceptor_name  = label                                              ,
                                          state             = _state_to_enum(_state_str(details))                ,
                                          launch_time       = str(details.get('LaunchTime', ''))                 )
