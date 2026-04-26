# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Status__Class
# Derived field — sc_status // 100 mapped to the HTTP status class.
# Enables a stacked-bar dashboard panel "Status code distribution over time"
# without baking the 5 buckets into every visualization's painless script.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Status__Class(str, Enum):
    INFORMATIONAL = '1xx'                                                            # 100-199
    SUCCESS       = '2xx'                                                            # 200-299
    REDIRECTION   = '3xx'                                                            # 300-399
    CLIENT_ERROR  = '4xx'                                                            # 400-499
    SERVER_ERROR  = '5xx'                                                            # 500-599
    OTHER         = 'other'                                                          # Anything outside 100-599 (rare; defensive)

    def __str__(self):
        return self.value
