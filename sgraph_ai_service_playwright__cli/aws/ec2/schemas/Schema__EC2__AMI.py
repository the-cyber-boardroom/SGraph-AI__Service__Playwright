# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__AMI
# Schema for a single Amazon Machine Image (AMI).
# `attached_instance_ids` is only populated by show / orphans flows that join
# AMIs with the instance list; list-amis leaves it empty.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id           import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Architecture     import Safe_Str__EC2__Architecture
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id      import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Launch_Time      import Safe_Str__EC2__Launch_Time
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Name             import Safe_Str__EC2__Name
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Root_Device_Type import Safe_Str__EC2__Root_Device_Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Snapshot_Id      import Safe_Str__EC2__Snapshot_Id


class Schema__EC2__AMI(Type_Safe):
    ami_id                : Safe_Str__EC2__AMI_Id
    name                  : Safe_Str__EC2__Name
    description           : Safe_Str__EC2__Name
    owner_id              : Safe_Str__EC2__Name
    created_at            : Safe_Str__EC2__Launch_Time
    public                : bool = False
    architecture          : Safe_Str__EC2__Architecture
    root_device_type      : Safe_Str__EC2__Root_Device_Type
    snapshot_ids          : list[Safe_Str__EC2__Snapshot_Id]
    attached_instance_ids : list[Safe_Str__EC2__Instance_Id]
