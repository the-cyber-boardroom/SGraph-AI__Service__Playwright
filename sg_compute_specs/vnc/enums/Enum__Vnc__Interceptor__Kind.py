# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Enum__Vnc__Interceptor__Kind
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vnc__Interceptor__Kind(str, Enum):
    NONE   = 'none'
    NAME   = 'name'
    INLINE = 'inline'

    def __str__(self):
        return self.value
