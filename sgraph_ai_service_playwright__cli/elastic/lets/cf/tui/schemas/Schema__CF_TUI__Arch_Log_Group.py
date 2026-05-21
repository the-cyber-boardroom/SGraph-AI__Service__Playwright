# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Arch_Log_Group
# One CloudWatch log group as the architecture view shows it. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Arch_Log_Group(Type_Safe):
    name           : str
    retention_days : int = 0
    stored_bytes   : int = 0
