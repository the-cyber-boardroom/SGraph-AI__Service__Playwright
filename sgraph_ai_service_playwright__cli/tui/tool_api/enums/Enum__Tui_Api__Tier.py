# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Enum__Tui_Api__Tier
# The capability ladder a TUI API action sits on. READ_ONLY is always-AUTO; WRITE+
# is gated by the execution center (confirm / dry-run / ALLOW_MUTATIONS) in B3.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Tui_Api__Tier(str, Enum):
    READ_ONLY   = 'read_only'
    WRITE       = 'write'
    CRUD        = 'crud'
    DESTRUCTIVE = 'destructive'

    def __str__(self):
        return self.value
