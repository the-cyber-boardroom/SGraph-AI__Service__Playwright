# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Logs__AWS__Client (in-memory)
# Covers: filter_events, start_query, get_query_results, wait_query.
# No mocks, no patches. Uses Logs__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Query__Result import Schema__Logs__Query__Result
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory import Logs__AWS__Client__In_Memory

_GROUP = '/aws/lambda/test-fn'
_NOW   = int(time.time() * 1000)


class TestFilterEvents:

    def test_empty_group_returns_empty(self):
        client = Logs__AWS__Client__In_Memory()
        resp   = client.filter_events(_GROUP, start_time=_NOW - 3600_000)
        assert resp.events == []

    def test_returns_events_in_group(self):
        client = Logs__AWS__Client__In_Memory()
        client.add_event(_GROUP, _NOW - 1000, 'START RequestId: abc')
        client.add_event(_GROUP, _NOW - 500,  'END RequestId: abc')
        resp = client.filter_events(_GROUP, start_time=_NOW - 3600_000)
        assert len(resp.events) == 2

    def test_filter_pattern_by_substring(self):
        client = Logs__AWS__Client__In_Memory()
        client.add_event(_GROUP, _NOW - 1000, 'INFO hello')
        client.add_event(_GROUP, _NOW - 500,  'ERROR something bad')
        resp = client.filter_events(_GROUP, start_time=_NOW - 3600_000, filter_pattern='ERROR')
        assert len(resp.events) == 1
        assert 'ERROR' in resp.events[0].message

    def test_start_time_filters_old_events(self):
        client = Logs__AWS__Client__In_Memory()
        client.add_event(_GROUP, _NOW - 7200_000, 'old event')  # 2h ago
        client.add_event(_GROUP, _NOW - 100,      'new event')
        resp = client.filter_events(_GROUP, start_time=_NOW - 3600_000)  # last 1h
        assert len(resp.events) == 1
        assert 'new' in resp.events[0].message

    def test_event_fields_populated(self):
        client = Logs__AWS__Client__In_Memory()
        client.add_event(_GROUP, _NOW, 'msg', stream='stream/abc', event_id='eid-1')
        resp = client.filter_events(_GROUP, start_time=_NOW - 1000)
        ev = resp.events[0]
        assert ev.event_id  == 'eid-1'
        assert ev.message   == 'msg'
        assert ev.timestamp == _NOW

    def test_limit_respected(self):
        client = Logs__AWS__Client__In_Memory()
        for i in range(10):
            client.add_event(_GROUP, _NOW + i, f'msg {i}')
        resp = client.filter_events(_GROUP, start_time=_NOW - 1000, limit=5)
        assert len(resp.events) == 5


class TestInsightsQuery:

    def test_start_query_returns_id(self):
        client = Logs__AWS__Client__In_Memory()
        qid    = client.start_query(_GROUP, 'fields @timestamp', _NOW - 3600_000, _NOW)
        assert qid == '1'

    def test_get_query_results_unknown_id(self):
        client = Logs__AWS__Client__In_Memory()
        result = client.get_query_results('99')
        assert result.status == 'Complete'
        assert result.rows   == []

    def test_get_query_results_with_canned_data(self):
        client = Logs__AWS__Client__In_Memory()
        client.add_query_result('1', [
            {'@timestamp': '2026-05-17 14:00:00.000', '@duration': '100', '@requestId': 'abc'},
        ])
        result = client.get_query_results('1')
        assert result.is_complete() is True
        assert len(result.rows) == 1
        assert result.rows[0].get('@duration') == '100'

    def test_wait_query_returns_complete(self):
        client = Logs__AWS__Client__In_Memory()
        client.add_query_result('5', [{'@timestamp': 'ts', '@duration': '50'}])
        result = client.wait_query('5', timeout_sec=5)
        assert result.is_complete() is True
