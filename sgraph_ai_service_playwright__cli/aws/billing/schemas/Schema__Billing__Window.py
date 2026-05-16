# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Billing__Window
# Date range and granularity for a Cost Explorer query. keyword stores the
# CLI verb ('last-48h', 'week', 'mtd', 'window') as an opaque string so the
# report can reproduce the original command in its header.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Granularity  import Enum__Billing__Granularity
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Str__Iso8601_Date  import Safe_Str__Iso8601_Date


class Schema__Billing__Window(Type_Safe):
    start       : Safe_Str__Iso8601_Date                                               # Inclusive start date (YYYY-MM-DD)
    end         : Safe_Str__Iso8601_Date                                               # Exclusive end date (YYYY-MM-DD) — Cost Explorer convention
    granularity : Enum__Billing__Granularity                                           # DAILY / HOURLY / MONTHLY
    keyword     : str                                                                  # Opaque verb string ('last-48h', 'week', 'mtd', 'window')
