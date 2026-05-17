# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__S3__Storage__Class
# S3 storage class labels returned by HeadObject / ListObjectsV2.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__S3__Storage__Class(str, Enum):
    STANDARD            = 'STANDARD'
    STANDARD_IA         = 'STANDARD_IA'
    ONEZONE_IA          = 'ONEZONE_IA'
    INTELLIGENT_TIERING = 'INTELLIGENT_TIERING'
    GLACIER             = 'GLACIER'
    GLACIER_IR          = 'GLACIER_IR'
    DEEP_ARCHIVE        = 'DEEP_ARCHIVE'
    REDUCED_REDUNDANCY  = 'REDUCED_REDUNDANCY'
    UNKNOWN             = 'UNKNOWN'
