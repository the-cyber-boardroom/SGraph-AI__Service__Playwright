# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__SSL__Protocol
# TLS/SSL protocol negotiated on the request (ssl_protocol TSV column).
# Pinned to the four versions CloudFront still emits; OTHER catches future
# versions we don't model yet (TLSv1.4 etc.).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__SSL__Protocol(str, Enum):
    TLSv1_0 = 'TLSv1.0'                                                              # Deprecated but legacy clients still attempt; CloudFront refuses
    TLSv1_1 = 'TLSv1.1'                                                              # Same
    TLSv1_2 = 'TLSv1.2'                                                              # Modern fallback
    TLSv1_3 = 'TLSv1.3'                                                              # Default for current clients
    OTHER   = 'OTHER'

    def __str__(self):
        return self.value
