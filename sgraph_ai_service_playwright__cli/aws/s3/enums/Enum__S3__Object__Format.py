# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__S3__Object__Format
# Detected render format of an S3 object.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__S3__Object__Format(str, Enum):
    JSON     = 'JSON'
    YAML     = 'YAML'
    MARKDOWN = 'MARKDOWN'
    CSV      = 'CSV'
    TEXT     = 'TEXT'
    GZIP     = 'GZIP'
    ZIP      = 'ZIP'
    BINARY   = 'BINARY'
