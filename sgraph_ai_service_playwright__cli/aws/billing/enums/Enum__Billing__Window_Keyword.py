# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Billing__Window_Keyword
# Named time-window presets surfaced as CLI sub-commands. The 'window' verb
# uses explicit start/end dates and does not need a keyword enum value.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Billing__Window_Keyword(str, Enum):
    LAST_48H      = 'LAST_48H'
    LAST_7D       = 'LAST_7D'
    MONTH_TO_DATE = 'MONTH_TO_DATE'

    def __str__(self):
        return self.value
