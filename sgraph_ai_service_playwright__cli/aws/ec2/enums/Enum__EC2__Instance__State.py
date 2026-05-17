# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Enum__EC2__Instance__State
# EC2 instance lifecycle states as reported by the AWS API, plus UNKNOWN as
# a fallback. Mirrors sgraph_ai_service_playwright__cli.ec2.enums.Enum__Instance__State
# but lives in the new aws/ec2/ namespace to keep the two trees decoupled
# until v0.2.30 consolidation.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__EC2__Instance__State(str, Enum):
    PENDING       = 'pending'
    RUNNING       = 'running'
    SHUTTING_DOWN = 'shutting-down'
    TERMINATED    = 'terminated'
    STOPPING      = 'stopping'
    STOPPED       = 'stopped'
    UNKNOWN       = 'unknown'

    def __str__(self):
        return self.value
