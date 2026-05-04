# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Vnc__Interceptor__Kind
# N5 selector — which mitmproxy interceptor (if any) the new stack should
# load at boot. Default: NONE. Operator picks one of:
#
#   NONE   — start mitmproxy with no interceptor (default)
#   NAME   — load a baked example by name from /opt/interceptors/examples/
#   INLINE — operator-supplied Python source baked at create time into
#            /opt/interceptors/runtime/active.py
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vnc__Interceptor__Kind(str, Enum):
    NONE   = 'none'
    NAME   = 'name'
    INLINE = 'inline'

    def __str__(self):
        return self.value
