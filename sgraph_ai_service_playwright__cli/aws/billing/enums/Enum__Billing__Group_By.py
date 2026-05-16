# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Billing__Group_By
# Dimension keys accepted by Cost Explorer for the GroupBy parameter.
# SERVICE is the default — groups spend by AWS service name.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Billing__Group_By(str, Enum):
    SERVICE        = 'SERVICE'
    USAGE_TYPE     = 'USAGE_TYPE'
    LINKED_ACCOUNT = 'LINKED_ACCOUNT'
    REGION         = 'REGION'

    def __str__(self):
        return self.value
