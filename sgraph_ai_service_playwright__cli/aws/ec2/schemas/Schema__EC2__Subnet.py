# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Subnet
# Schema for an EC2 Subnet, used by the `sg aws ec2 subnet` sub-app.
# `availability_zone_id` is the stable per-account zone ID (e.g. euw2-az1)
# whereas `availability_zone` is the human-facing name (e.g. eu-west-2a).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag        import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AZ       import Safe_Str__EC2__AZ
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__CIDR     import Safe_Str__EC2__CIDR
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Subnet_Id import Safe_Str__EC2__Subnet_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id    import Safe_Str__EC2__VPC_Id


class Schema__EC2__Subnet(Type_Safe):
    subnet_id                 : Safe_Str__EC2__Subnet_Id
    vpc_id                    : Safe_Str__EC2__VPC_Id
    cidr_block                : Safe_Str__EC2__CIDR
    availability_zone         : Safe_Str__EC2__AZ
    availability_zone_id      : str  = ''                                       # plain str: zone-id (e.g. euw2-az1) doesn't match the AZ regex
    available_ip_count        : int  = 0
    map_public_ip_on_launch   : bool = False
    state                     : str  = ''
    tags                      : Dict__EC2__Tag
