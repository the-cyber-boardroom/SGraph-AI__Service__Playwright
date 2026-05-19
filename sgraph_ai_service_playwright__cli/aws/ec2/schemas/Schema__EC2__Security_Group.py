# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Security_Group
# Full schema for an EC2 security group, used by the `sg aws ec2 sg` sub-app.
# Distinct from Schema__EC2__Security_Group__Ref (which is the summary used
# inside instance describe payloads).
#
# `attached_eni_ids` and `attached_instance_ids` are only populated by show /
# orphans flows that join with describe_network_interfaces; the list view
# leaves them empty for speed.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Value  import Safe_Str__AWS__Tag_Value
from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag             import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__SG_Rule   import List__Schema__EC2__SG_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__ENI_Id         import Safe_Str__EC2__ENI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id    import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id          import Safe_Str__EC2__SG_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id         import Safe_Str__EC2__VPC_Id


class Schema__EC2__Security_Group(Type_Safe):
    sg_id                 : Safe_Str__EC2__SG_Id
    name                  : Safe_Str__AWS__Tag_Value
    vpc_id                : Safe_Str__EC2__VPC_Id
    description           : str = ''
    owner_id              : str = ''
    ingress_rules         : List__Schema__EC2__SG_Rule
    egress_rules          : List__Schema__EC2__SG_Rule
    attached_eni_ids      : list[Safe_Str__EC2__ENI_Id]
    attached_instance_ids : list[Safe_Str__EC2__Instance_Id]
    tags                  : Dict__EC2__Tag
