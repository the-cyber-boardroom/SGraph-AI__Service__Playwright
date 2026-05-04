# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Stack__Create__Response
# Returned once by `sp vnc create`. Carries the generated operator password
# so the caller can stash it — there is no retrievable copy after this
# moment. Carries the active interceptor name for `sp vnc info`.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__IP__Address         import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Password       import Safe_Str__Vnc__Password
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Stack__Name    import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Stack__Create__Response(Type_Safe):
    stack_name           : Safe_Str__Vnc__Stack__Name
    aws_name_tag         : Safe_Str__Text                                           # EC2 console "Name" — always 'vnc-' prefixed
    instance_id          : Safe_Str__Instance__Id
    region               : Safe_Str__AWS__Region
    ami_id               : Safe_Str__AMI__Id
    instance_type        : Safe_Str__Text
    security_group_id    : Safe_Str__Id
    caller_ip            : Safe_Str__IP__Address                                    # /32 allowed on 443
    public_ip            : Safe_Str__Text                                           # Empty immediately after launch — AWS assigns async
    viewer_url           : Safe_Str__Url                                            # https://<ip>/ — chromium-VNC UI behind nginx (self-signed TLS)
    mitmweb_url          : Safe_Str__Url                                            # https://<ip>/mitmweb/ — proxied via nginx (same Basic auth)
    operator_username    : Safe_Str__Id                = 'operator'
    operator_password    : Safe_Str__Vnc__Password                                  # Returned once; used for nginx Basic auth AND MITM_PROXYAUTH
    interceptor_kind     : Enum__Vnc__Interceptor__Kind = Enum__Vnc__Interceptor__Kind.NONE
    interceptor_name     : Safe_Str__Id                                             # Set when kind=NAME (and 'inline' marker when kind=INLINE — recorded for sp vnc info)
    state                : Enum__Vnc__Stack__State     = Enum__Vnc__Stack__State.PENDING
