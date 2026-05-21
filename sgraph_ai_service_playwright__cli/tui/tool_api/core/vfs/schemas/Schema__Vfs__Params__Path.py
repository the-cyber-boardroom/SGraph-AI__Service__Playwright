# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs: Schema__Vfs__Params__Path
# Params for path-only VFS actions (list/tree/read/stat/mkdir/delete). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path import Safe_Str__File__Path


class Schema__Vfs__Params__Path(Type_Safe):
    path : Safe_Str__File__Path                                                   # file or folder path in the VFS
