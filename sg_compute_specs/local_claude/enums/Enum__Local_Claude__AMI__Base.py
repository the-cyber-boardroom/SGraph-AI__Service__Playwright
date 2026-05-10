# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — local-claude: Enum__Local_Claude__AMI__Base
# DLAMI is the default — it ships with the NVIDIA kernel driver which the
# Container Toolkit requires. AL2023 (plain, no drivers) kept for reference /
# future custom-AMI flows where drivers are baked in separately.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Local_Claude__AMI__Base(Enum):
    DLAMI  = 'dlami'   # Deep Learning OSS Nvidia Driver AMI — has kernel driver
    AL2023 = 'al2023'  # Plain Amazon Linux 2023 — NO NVIDIA drivers
