# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Neko__Stack__Info
# Stub. Mirrors Schema__Vnc__Stack__Info structure. Fields will be populated
# once the Neko experiment (v0.23.x) ships a real implementation.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Neko__Stack__Info(Type_Safe):
    stack_name  : Safe_Str__Text
    instance_id : Safe_Str__Instance__Id
    region      : Safe_Str__AWS__Region
    public_ip   : Safe_Str__Text
    state       : Safe_Str__Text
