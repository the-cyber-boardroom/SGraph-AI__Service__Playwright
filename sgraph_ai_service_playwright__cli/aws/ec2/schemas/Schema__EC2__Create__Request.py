# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Create__Request
# Validated parameters for launching a new EC2 instance.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                      import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id           import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type   import Safe_Str__EC2__Instance__Type


class Schema__EC2__Create__Request(Type_Safe):
    name             : str                          = ''
    instance_type    : Safe_Str__EC2__Instance__Type
    ami_id           : Safe_Str__EC2__AMI_Id
    key_pair         : str                          = ''
    subnet_id        : str                          = ''
    security_groups  : str                          = ''    # comma-separated SG IDs
    user_data        : str                          = ''    # cloud-init script content
    extra_tags_raw   : str                          = ''    # JSON string of extra k=v pairs
    wait_for_running : bool                         = True
