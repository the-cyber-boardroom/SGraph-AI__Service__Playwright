# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Billing__Metric
# Cost Explorer metric names. Values must match the AWS API strings exactly.
# UnblendedCost is the default — it represents actual charges before any
# enterprise discount or savings plan amortisation.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Billing__Metric(str, Enum):
    UNBLENDED_COST     = 'UnblendedCost'
    BLENDED_COST       = 'BlendedCost'
    NET_UNBLENDED_COST = 'NetUnblendedCost'
    AMORTIZED_COST     = 'AmortizedCost'

    def __str__(self):
        return self.value
