# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__Invocations__Reporter
# Covers: basic report, failed-only query, status handling.
# No mocks. Uses Logs__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Invocations__Reporter import Lambda__Invocations__Reporter
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory import Logs__AWS__Client__In_Memory

_FN  = 'test-function'
_NOW = int(time.time() * 1000)


def _reporter(canned_rows: list = None) -> Lambda__Invocations__Reporter:
    client = Logs__AWS__Client__In_Memory()
    if canned_rows is not None:
        client.add_query_result('1', canned_rows)
    return Lambda__Invocations__Reporter(logs_client=client)


class TestReport:

    def test_report_complete_status(self):
        reporter = _reporter([{'@timestamp': '2026-05-17 14:00:00.000', '@duration': '100'}])
        result   = reporter.report(_FN, since='1h')
        assert result.is_complete() is True

    def test_report_returns_rows(self):
        rows     = [{'@timestamp': 'ts', '@duration': '50', '@requestId': 'req1'}]
        reporter = _reporter(rows)
        result   = reporter.report(_FN)
        assert len(result.rows) == 1
        assert result.rows[0].get('@requestId') == 'req1'

    def test_report_empty_rows(self):
        reporter = _reporter([])
        result   = reporter.report(_FN)
        assert result.is_complete() is True
        assert result.rows == []

    def test_failed_only_flag(self):
        reporter = _reporter([])
        result   = reporter.report(_FN, failed_only=True)
        assert result.status in ('Complete', 'complete')

    def test_custom_limit(self):
        reporter = _reporter([{'@timestamp': 'ts', '@duration': '10'}])
        result   = reporter.report(_FN, limit=50)
        assert result.is_complete() is True
