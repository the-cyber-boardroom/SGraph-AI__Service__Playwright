# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — EC2__Stack__Mapper
# Maps a raw boto3 DescribeInstances dict → Schema__Stack__Info.
# Module-level helpers (tag_value, state_str, uptime_seconds) are importable
# by stack-specific mappers.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                             import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder                import TAG_STACK_NAME, TAG_STACK_TYPE, TAG_CALLER_IP
from sg_compute.core.node.schemas.Schema__Stack__Info           import Schema__Stack__Info


def tag_value(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def state_str(details: dict) -> str:
    raw = details.get('State', {})
    return raw.get('Name', '') if isinstance(raw, dict) else str(raw)


def uptime_seconds(details: dict) -> int:
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


def first_sg_id(details: dict) -> str:
    groups = details.get('SecurityGroups', [])
    return groups[0].get('GroupId', '') if groups else ''


class EC2__Stack__Mapper(Type_Safe):
    stack_type : str = ''

    def to_info(self, details: dict, region: str) -> Schema__Stack__Info:
        return Schema__Stack__Info(
            instance_id       = details.get('InstanceId', '')                    ,
            stack_name        = tag_value(details, TAG_STACK_NAME)               ,
            stack_type        = tag_value(details, TAG_STACK_TYPE) or self.stack_type,
            region            = region                                           ,
            state             = state_str(details)                               ,
            public_ip         = details.get('PublicIpAddress',  '') or ''        ,
            private_ip        = details.get('PrivateIpAddress', '') or ''        ,
            instance_type     = details.get('InstanceType', '')                  ,
            ami_id            = details.get('ImageId', '')                       ,
            security_group_id = first_sg_id(details)                            ,
            uptime_seconds    = uptime_seconds(details)                          ,
        )
