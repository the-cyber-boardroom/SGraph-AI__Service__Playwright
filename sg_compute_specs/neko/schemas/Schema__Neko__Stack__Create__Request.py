# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Schema__Neko__Stack__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.neko.primitives.Safe_Str__IP__Address                         import Safe_Str__IP__Address
from sg_compute_specs.neko.primitives.Safe_Str__Neko__Stack__Name                   import Safe_Str__Neko__Stack__Name


class Schema__Neko__Stack__Create__Request(Type_Safe):
    stack_name      : Safe_Str__Neko__Stack__Name                                   # auto-generated when empty
    region          : Safe_Str__AWS__Region
    caller_ip       : Safe_Str__IP__Address                                         # auto-detected when empty
    from_ami        : Safe_Str__AMI__Id                                             # latest AL2023 when empty
    instance_type   : Safe_Str__Text                                                # defaults to t3.large
    admin_password  : Safe_Str__Text                                                # Neko admin password; auto-generated when empty
    member_password : Safe_Str__Text                                                # Neko member password; auto-generated when empty
