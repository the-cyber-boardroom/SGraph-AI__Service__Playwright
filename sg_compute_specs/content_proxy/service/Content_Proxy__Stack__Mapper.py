# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Stack__Mapper
# Pure mapper: raw boto3 DescribeInstances detail → Schema__Content_Proxy__Stack__Info.
# Reads the cp:* tags for mode/tls. Per-component health is not derivable from EC2
# describe (defaults False) — the TUI fills it via live probes.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper                            import (tag_value, state_str,
                                                                                            first_sg_id)

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
            access_token = tag_value(details, TAG_ACCESS)                             )
