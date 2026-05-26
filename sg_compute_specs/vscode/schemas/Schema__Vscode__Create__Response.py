# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Schema__Vscode__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                      import Type_Safe
from sg_compute_specs.vscode.schemas.Schema__Vscode__Info import Schema__Vscode__Info


class Schema__Vscode__Create__Response(Type_Safe):
    stack_info : Schema__Vscode__Info = None
    password   : str = ''             # generated editor password — surfaced once, not persisted to a tag
    message    : str = ''
    elapsed_ms : int = 0
