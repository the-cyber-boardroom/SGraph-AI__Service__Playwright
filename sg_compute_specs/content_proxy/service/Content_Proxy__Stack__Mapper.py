# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Stack__Mapper
# Pure mapper: raw boto3 DescribeInstances detail → Schema__Content_Proxy__Stack__Info.
# Reads the cp:* tags for mode/tls. Per-component health is not derivable from EC2
# describe (defaults False) — the TUI fills it via live probes.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from datetime import datetime, timezone

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper                            import (tag_value, state_str,
                                                                                            first_sg_id, uptime_seconds)

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                  import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode                  import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Stack__State          import Enum__Content_Proxy__Stack__State
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info


TAG_MODE     = 'cp:mode'
TAG_TLS      = 'cp:tls'
TAG_EDGE     = 'cp:edge'
TAG_HOSTNAME = 'cp:hostname'
TAG_ACCESS   = 'cp:access-token'                                                    # recoverable for info (like sg va's AccessToken)
TAG_BROWSERS = 'cp:browser-count'                                                   # N interactive sg-playwright-vnc browsers → per-browser /browser/{i} URLs in info
TAG_ENGINE   = 'cp:browser-engine'                                                  # chromium | firefox (the fleet's autostarted engine)
TAG_TERMINATE_AT = 'TerminateAt'                                                    # ISO8601 deadman deadline (mirrors sg va) → list/info time-left


def _time_remaining(details: dict) -> tuple:                                        # (terminate_at, seconds_left) from the TerminateAt tag
    raw = tag_value(details, TAG_TERMINATE_AT) or ''
    if not raw:
        return '', 0
    try:
        t         = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        remaining = int((t - datetime.now(timezone.utc)).total_seconds())
        return raw, max(0, remaining)
    except Exception:
        return raw, 0


def _int_tag(details: dict, key: str) -> int:                                       # tag value → int (0 when absent/malformed)
    try:
        return int(tag_value(details, key) or 0)
    except (TypeError, ValueError):
        return 0



def _state(details: dict) -> Enum__Content_Proxy__Stack__State:
    try:
        return Enum__Content_Proxy__Stack__State(state_str(details))
    except ValueError:
        return Enum__Content_Proxy__Stack__State.UNKNOWN


def _enum(cls, raw: str, default):
    try:
        return cls(raw) if raw else default
    except ValueError:
        return default


class Content_Proxy__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Content_Proxy__Stack__Info:
        return Schema__Content_Proxy__Stack__Info(
            stack_name  = tag_value(details, 'StackName')                              ,
            instance_id = details.get('InstanceId', '')                               ,
            region      = region                                                      ,
            public_ip   = details.get('PublicIpAddress', '') or ''                    ,
            state       = _state(details)                                             ,
            mode         = _enum(Enum__Content_Proxy__Mode, tag_value(details, TAG_MODE),
                                 Enum__Content_Proxy__Mode.DIRECT_PROXY)              ,
            tls          = _enum(Enum__Content_Proxy__Tls,  tag_value(details, TAG_TLS),
                                 Enum__Content_Proxy__Tls.NONE)                       ,
            edge         = _enum(Enum__Content_Proxy__Edge, tag_value(details, TAG_EDGE),
                                 Enum__Content_Proxy__Edge.NONE)                      ,
            hostname     = tag_value(details, TAG_HOSTNAME)                           ,
            access_token = tag_value(details, TAG_ACCESS)                             ,
            browser_count  = _int_tag(details, TAG_BROWSERS)                          ,
            browser_engine = tag_value(details, TAG_ENGINE)                           ,
            uptime_seconds     = uptime_seconds(details)                              ,
            terminate_at       = _time_remaining(details)[0]                          ,
            time_remaining_sec = _time_remaining(details)[1]                          )
