# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Billing__Group
# Forward-compatible generic grouping schema for non-SERVICE dimensions
# (e.g. USAGE_TYPE, LINKED_ACCOUNT, REGION). group_key holds the dimension
# value. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Metric          import Enum__Billing__Metric
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Decimal__Currency__USD import Safe_Decimal__Currency__USD


class Schema__Billing__Group(Type_Safe):
    group_key  : str                                                                   # Dimension value (e.g. region name, account id, usage type)
    amount_usd : Safe_Decimal__Currency__USD                                           # Cost in USD (4dp precision)
    metric     : Enum__Billing__Metric                                                 # Metric used (e.g. UnblendedCost)
