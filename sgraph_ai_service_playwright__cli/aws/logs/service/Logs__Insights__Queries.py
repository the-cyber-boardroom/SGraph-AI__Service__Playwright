# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Logs__Insights__Queries
# Named CloudWatch Logs Insights query strings.
# The REPORT-line query reproduces the AWS console "Recent invocations" panel.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


QUERY__INVOCATIONS = (
    'fields @timestamp, @requestId, @logStream, @duration, @billedDuration, '
    '@memorySize, @maxMemoryUsed, @initDuration '
    '| filter @type = "REPORT" '
    '| sort @timestamp desc '
    '| limit 20'
)

QUERY__INVOCATIONS_FAILED = (
    'fields @timestamp, @requestId, @logStream, @duration, @billedDuration, '
    '@memorySize, @maxMemoryUsed, @initDuration '
    '| filter @type = "REPORT" and (ispresent(@error) or @duration >= @timeout * 1000) '
    '| sort @timestamp desc '
    '| limit 20'
)


class Logs__Insights__Queries(Type_Safe):

    def invocations_query(self, limit: int = 20, failed_only: bool = False) -> str:
        base = (
            f'fields @timestamp, @requestId, @logStream, @duration, @billedDuration, '
            f'@memorySize, @maxMemoryUsed, @initDuration '
        )
        if failed_only:
            base += '| filter @type = "REPORT" and (ispresent(@error) or @duration >= @timeout * 1000) '
        else:
            base += '| filter @type = "REPORT" '
        base += f'| sort @timestamp desc | limit {limit}'
        return base
