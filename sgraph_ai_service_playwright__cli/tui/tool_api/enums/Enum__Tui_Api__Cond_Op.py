# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Enum__Tui_Api__Cond_Op
# The comparison a precondition applies to a value dug out of provider.state().
# IN / NOT_IN treat the precondition value as a comma-separated set.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Tui_Api__Cond_Op(str, Enum):
    EQ     = 'eq'
    NEQ    = 'neq'
    IN     = 'in'
    NOT_IN = 'not_in'
    EXISTS = 'exists'
    ABSENT = 'absent'

    def __str__(self):
        return self.value
