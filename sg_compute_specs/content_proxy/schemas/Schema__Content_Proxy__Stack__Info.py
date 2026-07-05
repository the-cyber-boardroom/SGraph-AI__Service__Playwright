# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Stack__Info
# Public view of one content_proxy stack + per-component health. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id                     import Safe_Str__Instance__Id
from sg_compute.primitives.Safe_Str__AWS__Region                                    import Safe_Str__AWS__Region

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                  import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode                  import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Stack__State          import Enum__Content_Proxy__Stack__State
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.primitives.Safe_Str__Content_Proxy__Stack__Name  import Safe_Str__Content_Proxy__Stack__Name


class Schema__Content_Proxy__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Content_Proxy__Stack__Name
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    public_ip         : Safe_Str__Text
    state             : Enum__Content_Proxy__Stack__State = Enum__Content_Proxy__Stack__State.UNKNOWN
    mode              : Enum__Content_Proxy__Mode         = Enum__Content_Proxy__Mode.DIRECT_PROXY
    tls               : Enum__Content_Proxy__Tls          = Enum__Content_Proxy__Tls.NONE
    edge              : Enum__Content_Proxy__Edge         = Enum__Content_Proxy__Edge.NONE
    hostname          : Safe_Str__Text                                              # <slug>.sg-compute.sgraph.ai (Caddy auto-ACME); blank = IP only
    access_token      : Safe_Str__Text                                              # vault API key + /pw key + set-cookie token (from tag)
    firefox_count     : int = 0                                                     # N interactive Firefox browsers → /browser/firefox/{i} URLs
    active_script     : Safe_Str__Text
    # per-component health (the 5 services)
    mitmproxy_ext_ok  : bool = False
    mitmproxy_int_ok  : bool = False
    mitm_service_ok   : bool = False
    playwright_ok     : bool = False
    vault_app_ok      : bool = False
    vaults_present    : List[Safe_Str__Text]
