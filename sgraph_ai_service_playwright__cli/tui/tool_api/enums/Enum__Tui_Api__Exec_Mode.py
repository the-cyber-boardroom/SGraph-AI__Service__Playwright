# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Enum__Tui_Api__Exec_Mode
# How the execution center treats a call. AUTO runs it (READ_ONLY) / gates mutations;
# CONFIRM always asks; DRY_RUN previews and never dispatches.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Tui_Api__Exec_Mode(str, Enum):
    AUTO    = 'auto'
    CONFIRM = 'confirm'
    DRY_RUN = 'dry_run'

    def __str__(self):
        return self.value
