# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Evaluate__Return_Type
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Evaluate__Return_Type(str, Enum):                                       # Expected return from page.evaluate()
    JSON    = "json"
    STRING  = "string"
    NUMBER  = "number"
    BOOLEAN = "boolean"

    def __str__(self): return self.value
