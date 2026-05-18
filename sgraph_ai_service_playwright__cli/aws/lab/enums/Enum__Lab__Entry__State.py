# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Enum__Lab__Entry__State
# Lifecycle state of a ledger entry (a created resource).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lab__Entry__State(str, Enum):
    PENDING                     = 'pending'
    DELETED                     = 'deleted'
    FAILED                      = 'failed'
    ABANDONED                   = 'abandoned'
    DELETED_PENDING_CF_DISABLE  = 'deleted-pending-cf-disable'
