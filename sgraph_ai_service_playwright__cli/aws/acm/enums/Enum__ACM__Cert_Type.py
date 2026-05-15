# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__ACM__Cert_Type
# Certificate origin type as returned by ACM. AMAZON_ISSUED is the default for
# certs requested through ACM; IMPORTED covers operator-supplied cert/key pairs;
# PRIVATE is issued by a private CA.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ACM__Cert_Type(str, Enum):
    AMAZON_ISSUED = 'AMAZON_ISSUED'
    IMPORTED      = 'IMPORTED'
    PRIVATE       = 'PRIVATE'

    def __str__(self):
        return self.value
