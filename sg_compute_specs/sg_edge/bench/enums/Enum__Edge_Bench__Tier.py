# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Enum__Edge_Bench__Tier
# The three scenario tiers from doc 05: primitives (one thing in isolation),
# flows (composed), failures (failure injection).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Edge_Bench__Tier(str, Enum):
    PRIMITIVE = 'primitive'
    FLOW      = 'flow'
    FAILURE   = 'failure'

    def __str__(self):
        return self.value
