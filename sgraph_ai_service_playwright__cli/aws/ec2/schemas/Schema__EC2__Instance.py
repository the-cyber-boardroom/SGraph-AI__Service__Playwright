# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Instance
# Summary schema for a single EC2 instance as returned by list operations.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                      import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region       import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State           import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id           import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id      import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type   import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__IP_Address       import Safe_Str__EC2__IP_Address
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Key_Pair         import Safe_Str__EC2__Key_Pair
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Launch_Time      import Safe_Str__EC2__Launch_Time
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Name             import Safe_Str__EC2__Name


class Schema__EC2__Instance(Type_Safe):
    instance_id    : Safe_Str__EC2__Instance_Id
    instance_type  : Safe_Str__EC2__Instance__Type
    ami_id         : Safe_Str__EC2__AMI_Id
    state          : Enum__EC2__Instance__State     = Enum__EC2__Instance__State.UNKNOWN
    name           : Safe_Str__EC2__Name
    public_ip      : Safe_Str__EC2__IP_Address
    private_ip     : Safe_Str__EC2__IP_Address
    launch_time    : Safe_Str__EC2__Launch_Time
    key_name       : Safe_Str__EC2__Key_Pair
    region         : Safe_Str__AWS__Region
