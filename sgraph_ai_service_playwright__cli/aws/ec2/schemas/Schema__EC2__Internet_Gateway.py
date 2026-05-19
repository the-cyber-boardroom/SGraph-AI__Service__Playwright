# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Internet_Gateway
# Schema for an EC2 Internet Gateway, used by `sg aws ec2 igw` sub-app.
# `vpc_id` holds the attached VPC ID, or '' when the IGW is detached.
# `state` reflects the attachment state (available / attached / detached / …).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag      import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__IGW_Id import Safe_Str__EC2__IGW_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id import Safe_Str__EC2__VPC_Id


class Schema__EC2__Internet_Gateway(Type_Safe):
    igw_id : Safe_Str__EC2__IGW_Id
    vpc_id : Safe_Str__EC2__VPC_Id
    state  : str = ''
    tags   : Dict__EC2__Tag
