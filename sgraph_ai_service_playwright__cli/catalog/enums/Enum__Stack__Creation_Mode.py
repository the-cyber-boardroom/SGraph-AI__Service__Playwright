# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Stack__Creation_Mode
# The three launch paths the fractal-UI supports per plugin.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Stack__Creation_Mode(str, Enum):
    FRESH    = 'fresh'      # cold-boot from base AMI, run full user-data
    BAKE_AMI = 'bake-ami'   # cold-boot, then snapshot as a new AMI
    FROM_AMI = 'from-ami'   # boot from a pre-baked AMI (fast-boot, no user-data)
