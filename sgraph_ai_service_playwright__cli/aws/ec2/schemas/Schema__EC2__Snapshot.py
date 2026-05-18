# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Snapshot
# Schema for a single EBS snapshot as returned by describe_snapshots.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Int__EC2__GiB        import Safe_Int__EC2__GiB
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Launch_Time import Safe_Str__EC2__Launch_Time
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Name       import Safe_Str__EC2__Name
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Snapshot_Id import Safe_Str__EC2__Snapshot_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Volume_Id   import Safe_Str__EC2__Volume_Id


class Schema__EC2__Snapshot(Type_Safe):
    snapshot_id      : Safe_Str__EC2__Snapshot_Id
    volume_id        : Safe_Str__EC2__Volume_Id
    volume_size_gib  : Safe_Int__EC2__GiB
    description      : Safe_Str__EC2__Name
    state            : Safe_Str__EC2__Name
    started_at       : Safe_Str__EC2__Launch_Time
    owner_id         : Safe_Str__EC2__Name
