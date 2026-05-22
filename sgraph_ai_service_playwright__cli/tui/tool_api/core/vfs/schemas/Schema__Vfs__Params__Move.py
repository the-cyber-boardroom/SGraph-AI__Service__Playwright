# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs: Schema__Vfs__Params__Move
# Params for vfs.move. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path import Safe_Str__File__Path


class Schema__Vfs__Params__Move(Type_Safe):
    src : Safe_Str__File__Path                                                    # source path
    dst : Safe_Str__File__Path                                                    # destination path
