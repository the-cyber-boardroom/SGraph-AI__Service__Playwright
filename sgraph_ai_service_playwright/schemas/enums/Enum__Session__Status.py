# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Session__Status
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Session__Status(str, Enum):                                             # Current state of a session
    CREATED = "created"                                                             # Record exists, browser not yet launched
    ACTIVE  = "active"                                                              # Browser running, ready for actions
    IDLE    = "idle"                                                                # Browser running, no recent activity
    CLOSING = "closing"                                                             # Teardown in progress
    CLOSED  = "closed"                                                              # Browser gone, session ended cleanly
    ERROR   = "error"                                                               # Session in an error state

    def __str__(self): return self.value
