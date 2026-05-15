# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__ACM__Cert_Status
# Certificate lifecycle state as returned by ACM ListCertificates /
# DescribeCertificate. Maps directly to the ACM Status field.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ACM__Cert_Status(str, Enum):
    PENDING_VALIDATION    = 'PENDING_VALIDATION'
    ISSUED                = 'ISSUED'
    INACTIVE              = 'INACTIVE'
    EXPIRED               = 'EXPIRED'
    VALIDATION_TIMED_OUT  = 'VALIDATION_TIMED_OUT'
    REVOKED               = 'REVOKED'
    FAILED                = 'FAILED'

    def __str__(self):
        return self.value
