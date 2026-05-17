# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Bedrock__Check__Status
# Status values for a single Bedrock preflight check result.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Bedrock__Check__Status(str, Enum):
    PASS = 'PASS'
    WARN = 'WARN'
    FAIL = 'FAIL'
