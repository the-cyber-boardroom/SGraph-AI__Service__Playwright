# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Create__Response
# Returned once by `sp elastic create`. Carries the generated elastic password
# so the caller can stash it as an env var — there is no retrievable copy after
# this moment (matches `sp create`'s api_key_value behaviour).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region


class Schema__Elastic__Create__Response(Type_Safe):
    stack_name       : Safe_Str__Elastic__Stack__Name
    aws_name_tag     : Safe_Str__Text                                               # EC2 console "Name" column — always "elastic-" prefixed
    instance_id      : Safe_Str__Instance__Id
    region           : Safe_Str__AWS__Region
    ami_id           : Safe_Str__AMI__Id
    instance_type    : Safe_Str__Text                                               # See Request — Safe_Str__Text preserves the dot in instance type strings
    security_group_id: Safe_Str__Id
    caller_ip        : Safe_Str__IP__Address                                        # /32 allowed on 443
    public_ip        : Safe_Str__Text                                               # Empty immediately after launch — AWS assigns async; dots preserved by Text
    kibana_url       : Safe_Str__Url                                                # https://<ip>/ — self-signed TLS; Safe_Str__Url preserves "://" and ":port"
    elastic_username : Safe_Str__Id              = 'elastic'
    elastic_password : Safe_Str__Elastic__Password                                  # Returned once; never stored server-side
    state            : Enum__Elastic__State      = Enum__Elastic__State.PENDING
