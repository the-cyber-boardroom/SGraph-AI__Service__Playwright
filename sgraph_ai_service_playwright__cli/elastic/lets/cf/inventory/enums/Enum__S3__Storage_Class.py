# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__S3__Storage_Class
# S3 storage class returned in ListObjectsV2 responses. Initially every
# CloudFront real-time log object is STANDARD; lifecycle policies (which we
# don't have yet) would push older objects to STANDARD_IA / GLACIER.
# UNKNOWN catches anything AWS adds that we don't model.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__S3__Storage_Class(str, Enum):
    STANDARD            = 'STANDARD'
    STANDARD_IA         = 'STANDARD_IA'
    ONEZONE_IA          = 'ONEZONE_IA'
    INTELLIGENT_TIERING = 'INTELLIGENT_TIERING'
    GLACIER             = 'GLACIER'
    GLACIER_IR          = 'GLACIER_IR'
    DEEP_ARCHIVE        = 'DEEP_ARCHIVE'
    REDUCED_REDUNDANCY  = 'REDUCED_REDUNDANCY'                                      # Deprecated by AWS but still surfaces on legacy objects
    OUTPOSTS            = 'OUTPOSTS'
    EXPRESS_ONEZONE     = 'EXPRESS_ONEZONE'
    UNKNOWN             = 'UNKNOWN'                                                 # Anything AWS returns we don't model

    def __str__(self):
        return self.value
