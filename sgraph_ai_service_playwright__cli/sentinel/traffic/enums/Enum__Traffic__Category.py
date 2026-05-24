# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Traffic__Category
# Use-case class for a generated request: benign (should pass), malicious (should
# block), or malformed (structurally invalid, should block).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Traffic__Category(str, Enum):
    BENIGN    = 'benign'
    MALICIOUS = 'malicious'
    MALFORMED = 'malformed'
