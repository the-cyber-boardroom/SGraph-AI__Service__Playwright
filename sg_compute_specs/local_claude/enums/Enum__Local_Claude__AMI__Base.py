# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — local-claude: Enum__Local_Claude__AMI__Base
# For vLLM-in-Docker the NVIDIA drivers are delivered by the container toolkit,
# not a host-level DLAMI. AL2023 is the only base needed for v1.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Local_Claude__AMI__Base(Enum):
    AL2023 = 'al2023'
