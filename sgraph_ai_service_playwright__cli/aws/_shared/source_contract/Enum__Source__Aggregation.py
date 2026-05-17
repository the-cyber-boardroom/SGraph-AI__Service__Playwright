# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Enum__Source__Aggregation
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Source__Aggregation(str, Enum):
    COUNT  = 'count'
    SUM    = 'sum'
    AVG    = 'avg'
    MIN    = 'min'
    MAX    = 'max'
    UNIQUE = 'unique'
