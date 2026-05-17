# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Security_Group__Ref
# Reference to an EC2 security group (ID + name).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Value  import Safe_Str__AWS__Tag_Value
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id          import Safe_Str__EC2__SG_Id


class Schema__EC2__Security_Group__Ref(Type_Safe):
    group_id   : Safe_Str__EC2__SG_Id
    group_name : Safe_Str__AWS__Tag_Value
