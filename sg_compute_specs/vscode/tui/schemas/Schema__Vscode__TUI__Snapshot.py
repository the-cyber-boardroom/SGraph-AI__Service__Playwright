# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Schema__Vscode__TUI__Snapshot
# The one normalised snapshot every vscode TUI screen / the provider reads.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                            import Type_Safe
from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Stack import Schema__Vscode__TUI__Stack


class Schema__Vscode__TUI__Snapshot(Type_Safe):
    region      : str                            = ''
    captured_at : int                            = 0      # epoch seconds
    can_act     : bool                           = True   # may the screen/provider enable mutating actions?
    total       : int                            = 0
    stacks      : List[Schema__Vscode__TUI__Stack]
