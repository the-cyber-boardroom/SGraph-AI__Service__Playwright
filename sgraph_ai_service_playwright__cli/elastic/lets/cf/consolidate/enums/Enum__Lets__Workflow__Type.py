# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Lets__Workflow__Type
# The three LETS workflow families.  Each workflow type owns a compat-region
# folder under `lets/` with its own `lets-config.json`.
#   consolidate — many small units → one larger artefact (this slice)
#   compress    — records → rollups / aggregations (future)
#   expand      — one record → many derivatives (future)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lets__Workflow__Type(str, Enum):
    CONSOLIDATE = 'consolidate'
    COMPRESS    = 'compress'
    EXPAND      = 'expand'
    UNKNOWN     = 'unknown'

    def __str__(self):
        return self.value
