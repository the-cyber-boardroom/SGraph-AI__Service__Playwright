# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Firefox__Interceptor__Kind
# Selector for which mitmproxy interceptor (if any) the new Firefox stack
# should load at boot.
#
#   NONE   — start mitmproxy with no interceptor (default)
#   NAME   — load a baked example by name
#   INLINE — operator-supplied Python source baked at create time
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Firefox__Interceptor__Kind(str, Enum):
    NONE   = 'none'
    NAME   = 'name'
    INLINE = 'inline'

    def __str__(self):
        return self.value
