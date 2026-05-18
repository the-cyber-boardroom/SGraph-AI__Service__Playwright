# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Enum__Waker__State
# Machine-readable state labels for X-Waker-State header and structured logs.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Waker__State(str, Enum):
    NOT_FOUND = 'not_found'   # slug unrecognised — returned 404
    WARMING   = 'warming'     # EC2 stopped/pending/no-health — returned warming page
    STARTED   = 'started'     # EC2 was STOPPED — called start_instances, returned warming
    PROXIED   = 'proxied'     # EC2 running + healthy — proxied to vault-app
    ERROR     = 'error'       # proxy returned 5xx or threw
    UNKNOWN   = 'unknown'

    def __str__(self) -> str:
        return self.value
