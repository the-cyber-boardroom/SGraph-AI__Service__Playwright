# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__Stack__Mapper
# Pure mapper from raw boto3 describe_instances detail dict → Type_Safe
# Schema__Playwright__Stack__Info. No AWS calls, no network calls.
# Reads the `sg:with-mitmproxy` tag so info can report the flag without
# re-reading user-data. Mirrors Vnc__Stack__Mapper.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Info import Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client     import (TAG_ALLOWED_IP_KEY    ,
                                                                                               TAG_STACK_NAME_KEY    ,
                                                                                               TAG_WITH_MITMPROXY_KEY)


def _tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _state_str(details: dict) -> str:
    state_raw = details.get('State', {})
    return state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)


def _state_to_enum(state_str: str) -> Enum__Playwright__Stack__State:
    mapping = {'pending'      : Enum__Playwright__Stack__State.PENDING    ,
               'running'      : Enum__Playwright__Stack__State.RUNNING    ,
               'shutting-down': Enum__Playwright__Stack__State.TERMINATING,
               'stopping'     : Enum__Playwright__Stack__State.TERMINATING,
               'stopped'      : Enum__Playwright__Stack__State.TERMINATED ,
               'terminated'   : Enum__Playwright__Stack__State.TERMINATED }
    return mapping.get(state_str, Enum__Playwright__Stack__State.UNKNOWN)


class Playwright__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Playwright__Stack__Info:
        ip             = details.get('PublicIpAddress', '') or ''
        stack_name     = _tag(details, TAG_STACK_NAME_KEY)
        with_mitmproxy = _tag(details, TAG_WITH_MITMPROXY_KEY).lower() == 'true'
        return Schema__Playwright__Stack__Info(
            stack_name        = stack_name                                                                     ,
            aws_name_tag      = _tag(details, 'Name')                                                          ,
            instance_id       = details.get('InstanceId', '')                                                  ,
            region            = region                                                                         ,
            ami_id            = details.get('ImageId', '')                                                     ,
            instance_type     = details.get('InstanceType', '')                                                ,
            security_group_id = (details.get('SecurityGroups', [{}])[0].get('GroupId', '')
                                 if details.get('SecurityGroups') else '')                                     ,
            allowed_ip        = _tag(details, TAG_ALLOWED_IP_KEY)                                              ,
            public_ip         = ip                                                                             ,
            playwright_url    = f'http://{ip}:8000'    if ip else ''                                          ,
            with_mitmproxy    = with_mitmproxy                                                                 ,
            state             = _state_to_enum(_state_str(details))                                            ,
            launch_time       = str(details.get('LaunchTime', ''))                                             )
