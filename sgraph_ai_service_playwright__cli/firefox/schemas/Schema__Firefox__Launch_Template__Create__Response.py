# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Launch_Template__Create__Response
# Returned once on create — password shown only here (all ASG instances share it).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__Launch_Template__Create__Response(Type_Safe):
    lt_name           : Safe_Str__Firefox__Stack__Name                               # Launch Template name
    lt_id             : Safe_Str__Text                                                # lt-xxxxxxxxxxxxxxxx
    lt_version        : int = 0                                                       # version number (1 on create, increments on update)
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    sg_id             : Safe_Str__Text
    interceptor_label : Safe_Str__Text
    password          : Safe_Str__Text                                                # returned once — stash it; all ASG instances use this
    elapsed_ms        : int = 0
