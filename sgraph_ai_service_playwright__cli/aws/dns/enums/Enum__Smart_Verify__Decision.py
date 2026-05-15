# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Smart_Verify__Decision
# Classifies what kind of mutation was performed so verify_after_mutation knows
# which checks to run.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Smart_Verify__Decision(Enum):
    NEW_NAME = 'new_name'                                                        # Name+type did not exist before add — both auth + public checks run
    UPSERT   = 'upsert'                                                          # Name+type already existed; value changed — only auth check run
    DELETE   = 'delete'                                                          # Record deleted — only auth check run (confirm NXDOMAIN)

    def __str__(self):
        return self.value
