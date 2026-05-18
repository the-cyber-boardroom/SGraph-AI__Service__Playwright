# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Create__Request
# Validated parameters for launching a new EC2 instance.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                      import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag                 import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id           import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type   import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Key_Pair         import Safe_Str__EC2__Key_Pair
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Name             import Safe_Str__EC2__Name
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id_List       import Safe_Str__EC2__SG_Id_List
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Subnet_Id       import Safe_Str__EC2__Subnet_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__User_Data        import Safe_Str__EC2__User_Data


class Schema__EC2__Create__Request(Type_Safe):
    name             : Safe_Str__EC2__Name
    instance_type    : Safe_Str__EC2__Instance__Type
    ami_id           : Safe_Str__EC2__AMI_Id
    key_pair         : Safe_Str__EC2__Key_Pair
    subnet_id        : Safe_Str__EC2__Subnet_Id
    security_groups  : Safe_Str__EC2__SG_Id_List      # comma-separated SG IDs
    user_data        : Safe_Str__EC2__User_Data        # cloud-init script content
    extra_tags       : Dict__EC2__Tag
    wait_for_running : bool                         = True
