# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open_Design__Stack__Mapper
# Maps raw boto3 DescribeInstances dict → Schema__Open_Design__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from ephemeral_ec2.helpers.aws.EC2__Stack__Mapper                       import (tag_value      ,
                                                                                  state_str     ,
                                                                                  uptime_seconds,
                                                                                  first_sg_id   )
from ephemeral_ec2.helpers.aws.EC2__Tags__Builder                       import TAG_STACK_NAME, TAG_CALLER_IP
from ephemeral_ec2.stacks.open_design.schemas.Schema__Open_Design__Info import Schema__Open_Design__Info

TAG_OLLAMA = 'OllamaBaseUrl'
STACK_TYPE = 'open-design'


class Open_Design__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Open_Design__Info:
        public_ip = details.get('PublicIpAddress', '') or ''
        return Schema__Open_Design__Info(
            instance_id       = details.get('InstanceId', '')             ,
            stack_name        = tag_value(details, TAG_STACK_NAME)        ,
            region            = region                                    ,
            state             = state_str(details)                        ,
            public_ip         = public_ip                                 ,
            private_ip        = details.get('PrivateIpAddress', '') or '' ,
            instance_type     = details.get('InstanceType', '')           ,
            ami_id            = details.get('ImageId', '')                ,
            security_group_id = first_sg_id(details)                     ,
            caller_ip         = tag_value(details, TAG_CALLER_IP)         ,
            viewer_url        = f'https://{public_ip}/' if public_ip else '',
            has_ollama        = bool(tag_value(details, TAG_OLLAMA))      ,
            uptime_seconds    = uptime_seconds(details)                   ,
        )
