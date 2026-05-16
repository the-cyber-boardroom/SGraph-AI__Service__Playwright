# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Billing__Report__Builder
# Orchestrates Cost Explorer queries and maps raw boto3 ResultsByTime into a
# typed Schema__Billing__Report. The ce_client attribute is the single seam
# for test substitution — set it before calling build() to avoid real AWS
# calls. setup() provides lazy default initialisation.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime
from decimal import Decimal

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.billing.collections.List__Schema__Billing__Daily_Bucket import List__Schema__Billing__Daily_Bucket
from sgraph_ai_service_playwright__cli.aws.billing.collections.List__Schema__Billing__Line_Item    import List__Schema__Billing__Line_Item
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Granularity                import Enum__Billing__Granularity
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Group_By                   import Enum__Billing__Group_By
from sgraph_ai_service_playwright__cli.aws.billing.enums.Enum__Billing__Metric                     import Enum__Billing__Metric
from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Daily_Bucket           import Schema__Billing__Daily_Bucket
from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Line_Item              import Schema__Billing__Line_Item
from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Report                 import Schema__Billing__Report
from sgraph_ai_service_playwright__cli.aws.billing.schemas.Schema__Billing__Window                 import Schema__Billing__Window
from sgraph_ai_service_playwright__cli.aws.billing.service.Cost_Explorer__AWS__Client              import Cost_Explorer__AWS__Client


class Billing__Report__Builder(Type_Safe):

    ce_client : Cost_Explorer__AWS__Client = None                                    # Seam — set before build() to avoid real AWS calls

    def setup(self):                                                                   # Lazy-init the CE client when none was injected
        if self.ce_client is None:
            self.ce_client = Cost_Explorer__AWS__Client()
        return self

    def build(self, start: str, end: str, granularity: str,
              keyword: str, metric: str = 'UnblendedCost',
              group_by_key: str = 'SERVICE', top_n: int = 10,
              all_charges: bool = False) -> Schema__Billing__Report:
        self.setup()
        account_id  = self.ce_client.get_caller_account_id()
        raw_results = self.ce_client.get_cost_and_usage(
            start        = start                         ,
            end          = end                           ,
            granularity  = granularity                   ,
            metrics      = [metric]                      ,
            group_by     = [{'Type': 'DIMENSION', 'Key': group_by_key}],
            record_types = [] if all_charges else ['Usage'],  # [] = no filter; ['Usage'] = exclude credits/refunds/taxes
        )

        buckets     = List__Schema__Billing__Daily_Bucket()
        grand_total = Decimal('0')

        for result in raw_results:
            date_str    = result['TimePeriod']['Start']
            groups      = result.get('Groups', [])
            line_items  = List__Schema__Billing__Line_Item()
            bucket_total = Decimal('0')

            for g in groups:
                svc    = g['Keys'][0] if g['Keys'] else ''
                amount = Decimal(g['Metrics'][metric]['Amount'])
                bucket_total += amount
                line_items.append(Schema__Billing__Line_Item(
                    service    = svc                         ,
                    amount_usd = float(amount)               ,
                    metric     = Enum__Billing__Metric(metric),
                ))
            grand_total += bucket_total
            buckets.append(Schema__Billing__Daily_Bucket(
                date       = date_str          ,
                total_usd  = float(bucket_total),
                line_items = line_items         ,
            ))

        window = Schema__Billing__Window(
            start       = start                               ,
            end         = end                                 ,
            granularity = Enum__Billing__Granularity(granularity),
            keyword     = keyword                             ,
        )

        return Schema__Billing__Report(
            window       = window                              ,
            metric       = Enum__Billing__Metric(metric)       ,
            group_by     = Enum__Billing__Group_By(group_by_key),
            buckets      = buckets                             ,
            total_usd    = float(grand_total)                  ,
            account_id   = account_id                          ,
            currency     = 'USD'                               ,
            generated_at = str(datetime.date.today())          ,
        )
