# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Artefact__Sink
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Artefact__Sink(str, Enum):                                              # Where a captured artefact goes
    VAULT      = "vault"                                                            # SG/Send vault path
    INLINE     = "inline"                                                           # Base64 in HTTP response
    S3         = "s3"                                                               # Direct S3 write
    LOCAL_FILE = "local_file"                                                       # Filesystem path (dev/container only)

    def __str__(self): return self.value
