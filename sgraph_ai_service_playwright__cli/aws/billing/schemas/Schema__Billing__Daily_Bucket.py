# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Billing__Daily_Bucket
# One day's cost data: the calendar date, per-service line items, and the
# pre-computed day total. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.billing.collections.List__Schema__Billing__Line_Item import List__Schema__Billing__Line_Item
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Str__Iso8601_Date             import Safe_Str__Iso8601_Date
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Decimal__Currency__USD         import Safe_Decimal__Currency__USD


class Schema__Billing__Daily_Bucket(Type_Safe):
    date       : Safe_Str__Iso8601_Date                                                # Calendar date (YYYY-MM-DD) — TimePeriod.Start from Cost Explorer
    total_usd  : Safe_Decimal__Currency__USD                                           # Sum of all line items for this day
    line_items : List__Schema__Billing__Line_Item                                      # Per-service cost breakdown
