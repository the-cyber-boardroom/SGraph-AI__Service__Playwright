# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Playwright__Stack__Mapper
# Maps a raw boto3 DescribeInstances dict → Schema__Playwright__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper import (tag_value      ,
                                                                  state_str     ,
                                                                  uptime_seconds,
                                                                  first_sg_id   )
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder import TAG_STACK_NAME
from sg_compute_specs.playwright.schemas.Schema__Playwright__Info import Schema__Playwright__Info

TAG_WITH_MITMPROXY = 'StackWithMitmproxy'
TAG_TERMINATE_AT   = 'TerminateAt'
TAG_API_KEY        = 'StackApiKey'                                                 # FAST_API__AUTH__API_KEY__VALUE; surfaced by `sg playwright info`. Visible via ec2:DescribeInstances — same trade-off as vault-app's AccessToken tag.
STACK_TYPE         = 'playwright'

PLAYWRIGHT_PORT    = 8000                                                          # sg-playwright FastAPI — the public surface
SIDECAR_ADMIN_PORT = 8001                                                          # agent-mitmproxy admin API — only when with_mitmproxy
API_KEY_HEADER     = 'X-API-Key'                                                   # baked into the compose .env by the user-data builder; same name for both header and cookie


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


class Playwright__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Playwright__Info:
        public_ip               = details.get('PublicIpAddress', '') or ''
        with_mitmproxy          = tag_value(details, TAG_WITH_MITMPROXY) == 'true'
        terminate_at, remaining = _time_remaining(details)
        return Schema__Playwright__Info(
            instance_id        = details.get('InstanceId', '')                                ,
            stack_name         = tag_value(details, TAG_STACK_NAME)                           ,
            region             = region                                                       ,
            state              = state_str(details)                                           ,
            public_ip          = public_ip                                                    ,
            private_ip         = details.get('PrivateIpAddress', '') or ''                     ,
            instance_type      = details.get('InstanceType', '')                              ,
            ami_id             = details.get('ImageId', '')                                   ,
            security_group_id  = first_sg_id(details)                                          ,
            playwright_url     = f'http://{public_ip}:{PLAYWRIGHT_PORT}'    if public_ip else '',
            sidecar_admin_url  = (f'http://{public_ip}:{SIDECAR_ADMIN_PORT}'
                                  if (public_ip and with_mitmproxy) else '')                  ,
            with_mitmproxy     = with_mitmproxy                                                ,
            api_key            = tag_value(details, TAG_API_KEY)                               ,
            uptime_seconds     = uptime_seconds(details)                                       ,
            spot               = details.get('InstanceLifecycle', '') == 'spot'                ,
            terminate_at       = terminate_at                                                  ,
            time_remaining_sec = remaining                                                     ,
        )
