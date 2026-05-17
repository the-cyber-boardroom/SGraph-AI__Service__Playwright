# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Block_Device__Mapping
# EBS block device mapping attached to an EC2 instance.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Device_Name  import Safe_Str__EC2__Device_Name
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Volume_Id    import Safe_Str__EC2__Volume_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__BDM_Status   import Safe_Str__EC2__BDM_Status
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Int__EC2__GiB          import Safe_Int__EC2__GiB


class Schema__EC2__Block_Device__Mapping(Type_Safe):
    device_name           : Safe_Str__EC2__Device_Name
    volume_id             : Safe_Str__EC2__Volume_Id
    volume_size           : Safe_Int__EC2__GiB
    delete_on_termination : bool = True
    status                : Safe_Str__EC2__BDM_Status
