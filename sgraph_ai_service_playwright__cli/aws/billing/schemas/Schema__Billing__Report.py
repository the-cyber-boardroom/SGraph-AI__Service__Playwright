# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Billing__Report
# Top-level output of a billing query: window metadata, daily buckets,
# grand total, and provenance fields. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.billing.collections.List__Schema__Billing__Daily_Bucket import List__Schema__Billing__Daily_Bucket
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Group_By                   import Enum__Billing__Group_By
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Metric                     import Enum__Billing__Metric
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Decimal__Currency__USD            import Safe_Decimal__Currency__USD
from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Str__Iso8601_Date                 import Safe_Str__Iso8601_Date
from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Window                  import Schema__Billing__Window


class Schema__Billing__Report(Type_Safe):
    window       : Schema__Billing__Window                                             # Date range + granularity + keyword
    metric       : Enum__Billing__Metric                                               # Cost metric used for this report
    group_by     : Enum__Billing__Group_By                                             # Dimension used for grouping (default: SERVICE)
    buckets      : List__Schema__Billing__Daily_Bucket                                 # One bucket per day in the window
    total_usd    : Safe_Decimal__Currency__USD                                         # Grand total across all buckets
    account_id   : str                                                                 # AWS account id from STS get_caller_identity
    currency     : str                                                                 # Always 'USD' — multi-currency is out of scope for MVP
    generated_at : Safe_Str__Iso8601_Date                                             # Date the report was generated (YYYY-MM-DD)
