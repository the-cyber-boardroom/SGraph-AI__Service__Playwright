# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Protocol
# Wire protocol on the request (cs_protocol TSV column).
# CloudFront emits "http" / "https" / "ws" / "wss" lowercase; we normalise to
# uppercase via Enum value but keep the wire form lowercase to match what the
# parser sees.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Protocol(str, Enum):
    HTTP  = 'http'
    HTTPS = 'https'
    WS    = 'ws'
    WSS   = 'wss'
    OTHER = 'other'

    def __str__(self):
        return self.value
