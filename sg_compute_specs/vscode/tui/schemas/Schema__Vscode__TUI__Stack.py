# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Schema__Vscode__TUI__Stack
# One row in the TUI stacks dashboard — a normalised view of a Schema__Vscode__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vscode__TUI__Stack(Type_Safe):
    stack_name         : str  = ''
    instance_id        : str  = ''
    state              : str  = ''
    distribution       : str  = ''
    ingress            : str  = ''
    region             : str  = ''
    vscode_url         : str  = ''
    ssm_forward        : str  = ''
    spot               : bool = False
    time_remaining_sec : int  = 0
