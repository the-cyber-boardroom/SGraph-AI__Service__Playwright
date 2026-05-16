# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Billing__Line_Item
# One cost line within a daily bucket — a single AWS service's spend for
# that day. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Metric         import Enum__Billing__Metric
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Str__Aws_Service_Code import Safe_Str__Aws_Service_Code
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Decimal__Currency__USD import Safe_Decimal__Currency__USD


class Schema__Billing__Line_Item(Type_Safe):
    service    : Safe_Str__Aws_Service_Code                                            # AWS service name (e.g. 'Amazon EC2')
    amount_usd : Safe_Decimal__Currency__USD                                           # Cost in USD (4dp precision)
    metric     : Enum__Billing__Metric                                                 # Metric used (e.g. UnblendedCost)
