# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Schema__Vscode__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vscode__Delete__Response(Type_Safe):
    stack_name : str  = ''
    deleted    : bool = False
    message    : str  = ''
    elapsed_ms : int  = 0
