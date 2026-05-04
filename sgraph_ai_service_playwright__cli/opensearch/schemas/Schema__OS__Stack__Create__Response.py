# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__OS__Stack__Create__Response
# Returned once by `sp os create`. Carries the generated admin password so the
# caller can stash it as an env var — there is no retrievable copy after this
# moment (matches Schema__Elastic__Create__Response).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Password import Safe_Str__OS__Password
from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Stack__Name import Safe_Str__OS__Stack__Name


class Schema__OS__Stack__Create__Response(Type_Safe):
    stack_name        : Safe_Str__OS__Stack__Name
    aws_name_tag      : Safe_Str__Text                                              # EC2 console "Name" column — always "opensearch-" prefixed (per OS_NAMING)
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text                                              # See Request — Safe_Str__Text preserves the dot in instance type strings
    security_group_id : Safe_Str__Id
    caller_ip         : Safe_Str__IP__Address                                       # /32 allowed on 443
    public_ip         : Safe_Str__Text                                              # Empty immediately after launch — AWS assigns async; dots preserved by Text
    dashboards_url    : Safe_Str__Url                                               # https://<ip>/ — OpenSearch Dashboards behind self-signed TLS
    os_endpoint       : Safe_Str__Url                                               # https://<ip>:9200/ — OpenSearch REST API
    admin_username    : Safe_Str__Id              = 'admin'
    admin_password    : Safe_Str__OS__Password                                      # Returned once; never stored server-side
    state             : Enum__OS__Stack__State    = Enum__OS__Stack__State.PENDING
