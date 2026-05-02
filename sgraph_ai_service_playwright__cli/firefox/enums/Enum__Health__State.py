# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Health__State
# Three-state signal for each component in Schema__Firefox__Health.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Health__State(str, Enum):
    GREEN = 'green'
    AMBER = 'amber'
    RED   = 'red'
