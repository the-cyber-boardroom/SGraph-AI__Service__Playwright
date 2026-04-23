# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Stack__Component__Status
# Normalised lifecycle state across the three AWS services that make up an
# observability stack (AMP, OpenSearch, AMG). Each service exposes its own
# status vocabulary; Observability__Service maps them onto this enum so the
# FastAPI + CLI renderers have a single set of values to handle.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Stack__Component__Status(str, Enum):
    ACTIVE     = 'active'                                                           # Normal ready state
    CREATING   = 'creating'                                                         # Initial provision in progress
    UPDATING   = 'updating'                                                         # Config change in progress
    DELETING   = 'deleting'                                                         # Teardown in progress
    PROCESSING = 'processing'                                                       # OpenSearch generic "work in flight" state
    FAILED     = 'failed'                                                           # Terminal failure
    MISSING    = 'missing'                                                          # Component not found in the region
    UNKNOWN    = 'unknown'                                                          # Service returned a status we do not map

    def __str__(self):
        return self.value
