# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Enum__Tui_Api__Change_Kind
# The kind of a change-control entry (rendered into whatsnew.md / changelog.md).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Tui_Api__Change_Kind(str, Enum):
    FEATURE     = 'feature'
    FIX         = 'fix'
    DEPRECATION = 'deprecation'
    BREAKING    = 'breaking'
    CONFIG      = 'config'

    def __str__(self):
        return self.value
