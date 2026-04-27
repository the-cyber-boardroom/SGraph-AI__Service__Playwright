# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Pipeline__Verb
# Names the verb that drove a single pipeline run.  Stored on every
# Schema__Pipeline__Run journal doc so the operator can grep the journal by
# verb (`runs --verb events-load`).  Kept small on purpose — add more values
# only when a new verb actually persists a journal entry.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Pipeline__Verb(str, Enum):
    INVENTORY_LOAD = 'inventory-load'                                                 # `sp el lets cf inventory load`
    EVENTS_LOAD    = 'events-load'                                                    # `sp el lets cf events load`
    INVENTORY_WIPE = 'inventory-wipe'                                                 # `sp el lets cf inventory wipe`
    EVENTS_WIPE    = 'events-wipe'                                                    # `sp el lets cf events wipe`
    SG_SEND_LOAD   = 'sg-send-load'                                                   # `sp el lets cf sg-send load` (Phase C)
    UNKNOWN        = 'unknown'                                                        # Defensive default

    def __str__(self):
        return self.value
