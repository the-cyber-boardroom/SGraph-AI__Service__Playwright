# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__Stack__Mapper
# Maps a raw boto3 DescribeInstances dict → Schema__Vault_App__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper import (tag_value      ,
                                                                  state_str     ,
                                                                  uptime_seconds,
                                                                  first_sg_id   )
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder import TAG_STACK_NAME
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Info import Schema__Vault_App__Info

TAG_WITH_PLAYWRIGHT = 'StackWithPlaywright'
TAG_ENGINE          = 'StackEngine'
TAG_TERMINATE_AT    = 'TerminateAt'
STACK_TYPE          = 'vault-app'

VAULT_PORT = 8080


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


class Vault_App__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Vault_App__Info:
        public_ip               = details.get('PublicIpAddress', '') or ''
        terminate_at, remaining = _time_remaining(details)
        return Schema__Vault_App__Info(
            instance_id        = details.get('InstanceId', '')                       ,
            stack_name         = tag_value(details, TAG_STACK_NAME)                  ,
            region             = region                                              ,
            state              = state_str(details)                                  ,
            public_ip          = public_ip                                           ,
            private_ip         = details.get('PrivateIpAddress', '') or ''            ,
            instance_type      = details.get('InstanceType', '')                     ,
            ami_id             = details.get('ImageId', '')                          ,
            security_group_id  = first_sg_id(details)                                ,
            vault_url          = f'http://{public_ip}:{VAULT_PORT}' if public_ip else '' ,
            with_playwright    = tag_value(details, TAG_WITH_PLAYWRIGHT) == 'true'    ,
            container_engine   = tag_value(details, TAG_ENGINE)                      ,
            uptime_seconds     = uptime_seconds(details)                              ,
            spot               = details.get('InstanceLifecycle', '') == 'spot'      ,
            terminate_at       = terminate_at                                         ,
            time_remaining_sec = remaining                                            ,
        )
