# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__ENI
# Schema for an Elastic Network Interface, used by the `sg aws ec2 eni` sub-app.
#
# `security_group_ids` holds the raw SG ID strings attached to this ENI.
# `attachment_instance_id` is empty for standalone / fargate ENIs.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__EC2__ENI(Type_Safe):
    eni_id                : str = ''
    subnet_id             : str = ''
    vpc_id                : str = ''
    public_ip             : str = ''
    private_ip            : str = ''
    attachment_instance_id: str = ''
    attachment_status     : str = ''
    security_group_ids    : list = None
    description           : str = ''
    status                : str = ''
