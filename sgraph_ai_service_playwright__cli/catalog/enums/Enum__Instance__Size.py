# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Instance__Size
# T-shirt size abstraction. Plugins map these to concrete AWS instance types
# in their own capability detectors (never in this base enum).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Instance__Size(str, Enum):
    SMALL  = 'small'   # e.g. t3.small / t3.medium
    MEDIUM = 'medium'  # e.g. t3.large / m5.large
    LARGE  = 'large'   # e.g. m5.xlarge / c5.xlarge
