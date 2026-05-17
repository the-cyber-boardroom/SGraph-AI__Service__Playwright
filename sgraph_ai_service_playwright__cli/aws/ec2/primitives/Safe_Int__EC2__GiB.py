# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Int__EC2__GiB
# EBS volume size in gibibytes. AWS supports 1–65536 GiB for gp2/gp3.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__EC2__GiB(Safe_Int):
    min_value = 0
    max_value = 65536
