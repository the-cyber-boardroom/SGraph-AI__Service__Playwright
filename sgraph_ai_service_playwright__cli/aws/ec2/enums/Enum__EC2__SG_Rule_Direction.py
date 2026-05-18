# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Enum__EC2__SG_Rule_Direction
# Direction of an EC2 security-group rule. INGRESS rules govern inbound
# traffic; EGRESS rules govern outbound. No Literals — enum-only.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__EC2__SG_Rule_Direction(str, Enum):
    INGRESS = 'ingress'
    EGRESS  = 'egress'

    def __str__(self):
        return self.value
