# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Cert__Mode
# How a stack's TLS cert is obtained. P0 implements SELF_SIGNED only; the two
# Let's Encrypt modes are reserved for the P2 ACME phase (see the TLS PoC doc).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Cert__Mode(Enum):
    SELF_SIGNED     = 'self-signed'
    LETSENCRYPT_IP  = 'letsencrypt-ip'
    LETSENCRYPT_DNS = 'letsencrypt-dns'
