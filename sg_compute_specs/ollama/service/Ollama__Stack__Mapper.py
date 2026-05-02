# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama__Stack__Mapper
# Maps raw boto3 DescribeInstances dict → Schema__Ollama__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.helpers.aws.EC2__Stack__Mapper             import (tag_value      ,
                                                                       state_str     ,
                                                                       uptime_seconds,
                                                                       first_sg_id   )
from sg_compute.helpers.aws.EC2__Tags__Builder             import TAG_STACK_NAME
from sg_compute_specs.ollama.schemas.Schema__Ollama__Info import Schema__Ollama__Info

TAG_MODEL  = 'StackModel'
STACK_TYPE = 'ollama'

GPU_INSTANCE_PREFIXES = ('g4dn', 'g5', 'g6', 'p3', 'p4', 'p5')


def gpu_count_for(instance_type: str) -> int:
    prefix = instance_type.split('.')[0] if '.' in instance_type else ''
    return 1 if any(prefix.startswith(p) for p in GPU_INSTANCE_PREFIXES) else 0


class Ollama__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Ollama__Info:
        private_ip    = details.get('PrivateIpAddress', '') or ''
        instance_type = details.get('InstanceType', '')
        return Schema__Ollama__Info(
            instance_id       = details.get('InstanceId', '')             ,
            stack_name        = tag_value(details, TAG_STACK_NAME)        ,
            region            = region                                    ,
            state             = state_str(details)                        ,
            public_ip         = details.get('PublicIpAddress', '') or ''  ,
            private_ip        = private_ip                                ,
            instance_type     = instance_type                             ,
            ami_id            = details.get('ImageId', '')                ,
            security_group_id = first_sg_id(details)                     ,
            model_name        = tag_value(details, TAG_MODEL)             ,
            api_base_url      = f'http://{private_ip}:11434/v1' if private_ip else '',
            uptime_seconds    = uptime_seconds(details)                   ,
            gpu_count         = gpu_count_for(instance_type)              ,
        )
