# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Component__Delete__Outcome
# Result code returned by per-component delete operations. DELETED means AWS
# accepted the request — for asynchronous services (OpenSearch) the resource
# may still be visible in the console while it tears down.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Component__Delete__Outcome(str, Enum):
    DELETED    = 'deleted'                                                          # AWS accepted the delete request
    NOT_FOUND  = 'not_found'                                                        # Component was already absent; nothing to do
    FAILED     = 'failed'                                                           # AWS returned an error other than NotFound

    def __str__(self):
        return self.value
