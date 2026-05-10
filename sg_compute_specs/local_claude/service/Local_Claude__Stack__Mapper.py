# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Local_Claude__Stack__Mapper
# Maps raw boto3 DescribeInstances dict → Schema__Local_Claude__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper  import (tag_value      ,
                                                                    state_str     ,
                                                                    uptime_seconds,
                                                                    first_sg_id   )
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder  import TAG_STACK_NAME
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Info import Schema__Local_Claude__Info

TAG_MODEL        = 'StackModel'
TAG_DISK_GB      = 'StackDiskGB'
TAG_TOOL_PARSER  = 'StackToolParser'
TAG_TERMINATE_AT = 'TerminateAt'
STACK_TYPE       = 'local-claude'


def _time_remaining(details: dict) -> tuple:
    raw = tag_value(details, TAG_TERMINATE_AT) or ''
    if not raw:
        return '', 0
    try:
        t         = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        remaining = int((t - datetime.now(timezone.utc)).total_seconds())
        return raw, max(0, remaining)
    except Exception:
        return raw, 0

GPU_INSTANCE_PREFIXES = ('g4dn', 'g5', 'g6', 'p3', 'p4', 'p5')


def gpu_count_for(instance_type: str) -> int:
    prefix = instance_type.split('.')[0] if '.' in instance_type else ''
    return 1 if any(prefix.startswith(p) for p in GPU_INSTANCE_PREFIXES) else 0


class Local_Claude__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Local_Claude__Info:
        instance_type           = details.get('InstanceType', '')
        terminate_at, remaining = _time_remaining(details)
        return Schema__Local_Claude__Info(
            instance_id        = details.get('InstanceId', '')             ,
            stack_name         = tag_value(details, TAG_STACK_NAME)        ,
            region             = region                                    ,
            state              = state_str(details)                        ,
            public_ip          = details.get('PublicIpAddress', '') or ''  ,
            private_ip         = details.get('PrivateIpAddress', '') or ''  ,
            instance_type      = instance_type                             ,
            ami_id             = details.get('ImageId', '')                ,
            security_group_id  = first_sg_id(details)                     ,
            model_name         = tag_value(details, TAG_MODEL)             ,
            tool_parser        = tag_value(details, TAG_TOOL_PARSER)       ,
            disk_size_gb       = int(tag_value(details, TAG_DISK_GB) or 0) ,
            uptime_seconds     = uptime_seconds(details)                   ,
            gpu_count          = gpu_count_for(instance_type)              ,
            spot               = details.get('InstanceLifecycle', '') == 'spot' ,
            terminate_at       = terminate_at                              ,
            time_remaining_sec = remaining                                 ,
        )
