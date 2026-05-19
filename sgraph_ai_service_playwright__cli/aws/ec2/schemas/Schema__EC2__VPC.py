# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__VPC
# Schema for an EC2 Virtual Private Cloud, used by the `sg aws ec2 vpc` sub-app.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag       import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__CIDR    import Safe_Str__EC2__CIDR
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id  import Safe_Str__EC2__VPC_Id


class Schema__EC2__VPC(Type_Safe):
    vpc_id            : Safe_Str__EC2__VPC_Id
    cidr_block        : Safe_Str__EC2__CIDR
    is_default        : bool = False
    state             : str  = ''
    dhcp_options_id   : str  = ''
    instance_tenancy  : str  = ''
    tags              : Dict__EC2__Tag
