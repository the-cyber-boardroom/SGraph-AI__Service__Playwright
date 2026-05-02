# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__AMI__Bake__State
# Progress states for a BAKE_AMI creation mode request.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__AMI__Bake__State(str, Enum):
    BAKING = 'baking'   # instance running; CreateImage in progress
    READY  = 'ready'    # AMI available; instance may be terminated
    FAILED = 'failed'   # bake step failed; see detail message
