# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Stack__Creation_Mode
# Determines whether to launch from a baked AMI or from scratch.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Stack__Creation_Mode(str, Enum):
    FRESH    = 'fresh'     # full install from scratch via user-data
    BAKE_AMI = 'bake-ami'  # launch fresh then stop + create AMI
    FROM_AMI = 'from-ami'  # launch from a pre-baked AMI (fast boot)
