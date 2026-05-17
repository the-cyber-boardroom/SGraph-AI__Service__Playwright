# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Origin__Protocol
# CloudFront OriginProtocolPolicy values for custom-origin connections.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Origin__Protocol(str, Enum):
    HTTPS_ONLY   = 'https-only'
    HTTP_ONLY    = 'http-only'
    MATCH_VIEWER = 'match-viewer'

    def __str__(self):
        return self.value
