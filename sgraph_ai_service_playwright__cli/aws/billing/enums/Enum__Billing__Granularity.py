# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Billing__Granularity
# Time granularity values accepted by the Cost Explorer GetCostAndUsage API.
# DAILY is the default for all billing window commands.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Billing__Granularity(str, Enum):
    DAILY   = 'DAILY'
    HOURLY  = 'HOURLY'
    MONTHLY = 'MONTHLY'

    def __str__(self):
        return self.value
