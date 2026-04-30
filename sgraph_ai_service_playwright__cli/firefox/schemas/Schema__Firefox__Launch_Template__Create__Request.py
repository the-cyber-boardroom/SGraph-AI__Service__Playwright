# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Launch_Template__Create__Request
# Pure data. sg_id is required — caller pre-creates the SG and passes it in.
# ami_id is required — typically the output of sp firefox ami create.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Interceptor__Source import Safe_Str__Firefox__Interceptor__Source
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Interceptor__Choice import Schema__Firefox__Interceptor__Choice
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__Launch_Template__Create__Request(Type_Safe):
    name          : Safe_Str__Firefox__Stack__Name                                   # LT name; auto-generated when empty
    region        : Safe_Str__AWS__Region
    ami_id        : Safe_Str__AMI__Id                                                # required — Firefox AMI from sp firefox ami create
    instance_type : Safe_Str__Text                                                   # defaults to t3.medium
    sg_id         : Safe_Str__Text                                                   # required — pre-existing SG (caller manages lifecycle)
    interceptor   : Schema__Firefox__Interceptor__Choice
    env_source    : Safe_Str__Firefox__Interceptor__Source                           # raw .env content; allows #/newlines/URLs
    password      : Safe_Str__Firefox__Interceptor__Source                           # all instances share this password; auto-generated when empty
    fast_boot     : bool = True                                                      # render_fast (AMI has docker images baked); False = full AL2023 install
