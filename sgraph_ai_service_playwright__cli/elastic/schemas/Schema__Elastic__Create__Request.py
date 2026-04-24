# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Create__Request
# Inputs for `sp elastic create [NAME]`. All fields optional — the service
# generates a random name, detects the caller's public IP, and picks defaults
# for instance type / AMI when those are empty.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region


class Schema__Elastic__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Elastic__Stack__Name = ''                             # Empty → service generates "elastic-{adj}-{scientist}"
    region        : Safe_Str__AWS__Region          = ''                             # Empty → resolved from AWS_Config
    instance_type : Safe_Str__Text                 = ''                             # Safe_Str__Text preserves the dot in "t3.medium"; Safe_Str__Id would coerce to "t3_medium"
    from_ami      : Safe_Str__AMI__Id              = ''                             # Empty → latest AL2023 resolved by service
    caller_ip     : Safe_Str__IP__Address          = ''                             # Empty → service calls Caller__IP__Detector
