# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Enum__ALB__Protocol
# ALB protocol values (HTTP, HTTPS, TCP).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ALB__Protocol(str, Enum):
    HTTP    = 'HTTP'
    HTTPS   = 'HTTPS'
    TCP     = 'TCP'
    UNKNOWN = 'unknown'

    def __str__(self):
        return self.value
