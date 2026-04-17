# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Session__Lifetime
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Session__Lifetime(str, Enum):                                           # Caller's lifetime expectation
    EPHEMERAL              = "ephemeral"                                            # One request; closed immediately
    PERSISTENT_SINGLE      = "persistent_single"                                    # Persists across HTTP requests; single container
    PERSISTENT_DISTRIBUTED = "persistent_distributed"                               # Not supported; reserved for future

    def __str__(self): return self.value
