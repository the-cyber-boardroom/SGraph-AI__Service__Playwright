# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__Invocations__Reporter
# Runs a CloudWatch Logs Insights query for Lambda REPORT lines and returns
# the result rows. Reproduces the AWS console "Recent invocations" table.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client               import Logs__AWS__Client
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__Insights__Queries         import Logs__Insights__Queries
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__Time__Parser              import Logs__Time__Parser
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Query__Result     import Schema__Logs__Query__Result


class Lambda__Invocations__Reporter(Type_Safe):
    logs_client   : Logs__AWS__Client      = None
    time_parser   : Logs__Time__Parser     = None
    query_builder : Logs__Insights__Queries = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.logs_client is None:
            self.logs_client = Logs__AWS__Client()
        if self.time_parser is None:
            self.time_parser = Logs__Time__Parser()
        if self.query_builder is None:
            self.query_builder = Logs__Insights__Queries()

    def report(self,
               function_name : str,
               since         : str  = '1h',
               limit         : int  = 20,
               failed_only   : bool = False,
               ) -> Schema__Logs__Query__Result:
        log_group  = f'/aws/lambda/{function_name}'
        start_time = self.time_parser.parse_optional(since, 3600 * 1000)
        end_time   = self.time_parser.now_ms()
        query      = self.query_builder.invocations_query(limit=limit, failed_only=failed_only)
        query_id   = self.logs_client.start_query(
            log_group  = log_group,
            query      = query,
            start_time = start_time,
            end_time   = end_time,
        )
        return self.logs_client.wait_query(query_id)
