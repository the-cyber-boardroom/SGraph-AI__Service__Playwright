# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Playwright__Stack__State
# Lifecycle state for an ephemeral Playwright FastAPI stack running as a pod
# on a host. Mapped from the host-plane pod status string. Mirrors the sister
# sections' state vocabulary where it overlaps.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Playwright__Stack__State(str, Enum):
    PENDING  = 'pending'                                                            # start accepted, container not yet reported running
    RUNNING  = 'running'                                                            # pod container is up
    EXITED   = 'exited'                                                             # pod container stopped
    REMOVED  = 'removed'                                                            # pod removed from the host
    UNKNOWN  = 'unknown'                                                            # anything the host-plane returns we don't model

    def __str__(self):
        return self.value
