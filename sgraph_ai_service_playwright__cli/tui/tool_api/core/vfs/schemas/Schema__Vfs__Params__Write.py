# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs: Schema__Vfs__Params__Write
# Params for vfs.write. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path import Safe_Str__File__Path


class Schema__Vfs__Params__Write(Type_Safe):
    path    : Safe_Str__File__Path                                                # destination path
    content : str                                                                 # UTF-8 text content to write
