# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Enum__Setup__State
# State of a single setup area after a check() call.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Setup__State(str, Enum):
    OK      = 'ok'       # resource present and matches expected config
    MISSING = 'missing'  # resource not present at all
    DRIFT   = 'drift'    # present but config differs from expected
    ERROR   = 'error'    # couldn't read state (permission denied, network, etc.)
    UNKNOWN = 'unknown'  # check not yet run

    def __str__(self):
        return self.value
