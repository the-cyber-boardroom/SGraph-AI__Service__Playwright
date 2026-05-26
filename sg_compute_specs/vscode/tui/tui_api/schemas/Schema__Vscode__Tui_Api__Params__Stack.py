# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui/tui_api: Schema__Vscode__Tui_Api__Params__Stack
# Params for stack-scoped actions (delete). Drives the action input JSON Schema.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vscode__Tui_Api__Params__Stack(Type_Safe):
    stack_name : str = ''
