# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Instance__Detail
# Full instance detail schema returned by the describe operation.
# Includes networking, attached volumes, and all tags.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN                  import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region               import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag                         import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Block_Device__Mapping import List__Schema__EC2__Block_Device__Mapping
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Security_Group__Ref  import List__Schema__EC2__Security_Group__Ref
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State                   import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id                   import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Architecture             import Safe_Str__EC2__Architecture
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__DNS_Name                 import Safe_Str__EC2__DNS_Name
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__IP_Address               import Safe_Str__EC2__IP_Address
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id              import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type           import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Key_Pair                 import Safe_Str__EC2__Key_Pair
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Launch_Time              import Safe_Str__EC2__Launch_Time
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Name                     import Safe_Str__EC2__Name
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Platform                 import Safe_Str__EC2__Platform
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Root_Device_Type         import Safe_Str__EC2__Root_Device_Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Subnet_Id               import Safe_Str__EC2__Subnet_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id                   import Safe_Str__EC2__VPC_Id


class Schema__EC2__Instance__Detail(Type_Safe):
    instance_id          : Safe_Str__EC2__Instance_Id
    instance_type        : Safe_Str__EC2__Instance__Type
    ami_id               : Safe_Str__EC2__AMI_Id
    state                : Enum__EC2__Instance__State   = Enum__EC2__Instance__State.UNKNOWN
    name                 : Safe_Str__EC2__Name
    public_ip            : Safe_Str__EC2__IP_Address
    public_dns           : Safe_Str__EC2__DNS_Name
    private_ip           : Safe_Str__EC2__IP_Address
    private_dns          : Safe_Str__EC2__DNS_Name
    launch_time          : Safe_Str__EC2__Launch_Time
    key_name             : Safe_Str__EC2__Key_Pair
    region               : Safe_Str__AWS__Region
    vpc_id               : Safe_Str__EC2__VPC_Id
    subnet_id            : Safe_Str__EC2__Subnet_Id
    architecture         : Safe_Str__EC2__Architecture
    platform             : Safe_Str__EC2__Platform
    iam_instance_profile : Safe_Str__AWS__ARN
    root_device_type     : Safe_Str__EC2__Root_Device_Type
    tags                 : Dict__EC2__Tag
    security_groups      : List__Schema__EC2__Security_Group__Ref
    block_devices        : List__Schema__EC2__Block_Device__Mapping
