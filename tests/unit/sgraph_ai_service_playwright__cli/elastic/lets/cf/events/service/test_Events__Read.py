# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Events__Read
# Drives list_runs and health against in-memory subclasses.  No mocks.
# Tests parse_run_bucket against canned ES bucket dicts; tests health
# against canned find()/count_indices_by_pattern responses + canned
# inventory _count responses driven through Inventory__HTTP__Client__In_Memory's
# Recording_Requests pattern.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Events__Dashboard__Ids import DASHBOARD_ID
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Read import Events__Read, parse_run_bucket

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory             import Kibana__Saved_Objects__Client__In_Memory


# ─── parse_run_bucket — pure function ────────────────────────────────────────

class test_parse_run_bucket(TestCase):

    def test_full_bucket(self):
        bucket = {
            'key'             : '20260426T154435Z-cf-realtime-events-load-eb40',
            'doc_count'       : 565,
            'file_count'      : {'value': 50},
            'bytes_total'     : {'value': 64193.0},
            'earliest_event'  : {'value': 1, 'value_as_string': '2026-04-25T00:00:17.167Z'},
            'latest_event'    : {'value': 2, 'value_as_string': '2026-04-25T23:59:50.000Z'},
            'earliest_loaded' : {'value': 3, 'value_as_string': '2026-04-26T15:44:35.000Z'},
            'latest_loaded'   : {'value': 4, 'value_as_string': '2026-04-26T15:44:47.000Z'},
        }
        s = parse_run_bucket(bucket)
        assert str(s.pipeline_run_id) == '20260426T154435Z-cf-realtime-events-load-eb40'
        assert s.event_count          == 565
        assert s.file_count           == 50
        assert s.bytes_total          == 64_193

    def test_missing_sub_aggs_default_to_zeros(self):
        s = parse_run_bucket({'key': 'r1', 'doc_count': 5})
        assert s.event_count    == 5
        assert s.file_count     == 0
        assert s.bytes_total    == 0
        assert str(s.earliest_event) == ''


# ─── list_runs ───────────────────────────────────────────────────────────────

class _Fake_Response:                                                               # Minimal interface — same pattern as slice 1's Recording_Requests
    def __init__(self, status_code, json_body=None, text=''):
        self.status_code = status_code
        self.text        = text
        self._json       = json_body
    def json(self):
        if self._json is None:
            raise ValueError('not JSON')
        return self._json


class _Recording_HTTP_Client(Inventory__HTTP__Client__In_Memory):                   # Adds a request() override on top of the in-memory subclass
    request_log    : list
    response_queue : list

    def request(self, method, url, *, headers=None, data=None):
        self.request_log.append((method, url))
        if not self.response_queue:
            raise RuntimeError(f'no canned response for {method} {url}')
        return self.response_queue.pop(0)


def build_reader(response_queue=None,
                  fixture_count_response=(),
                  data_view_present=True,
                  dashboard_present=True):
    http = _Recording_HTTP_Client(bulk_calls=[], fixture_response=(),
                                   delete_pattern_calls=[], fixture_delete_pattern_response=(),
                                   count_pattern_calls=[], fixture_count_response=fixture_count_response,
                                   aggregate_calls=[], fixture_run_buckets=[],
                                   request_log=[], response_queue=response_queue or [])
    fixture_find = {}
    if data_view_present:
        fixture_find['index-pattern'] = [{'id': 'dv-uuid', 'type': 'index-pattern',
                                            'title': 'sg-cf-events-*', 'updated_at': '2026-04-26T16:00:00Z'}]
    if dashboard_present:
        fixture_find['dashboard'] = [{'id': DASHBOARD_ID, 'type': 'dashboard',
                                       'title': 'CloudFront Logs - Events Overview', 'updated_at': '2026-04-26T16:00:00Z'}]
    kb = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                   dashboard_calls=[], harden_calls=[],
                                                   delete_object_calls=[], import_calls=[],
                                                   find_calls=[], fixture_find_objects=fixture_find)
    return Events__Read(http_client=http, kibana_client=kb)


class test_Events__Read__list_runs(TestCase):

    def test_empty_buckets_returns_empty_list(self):                                # _search returns no aggregations → empty list
        es_response = {'aggregations': {'by_run': {'buckets': []}}}
        reader = build_reader(response_queue=[_Fake_Response(200, json_body=es_response)])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        assert len(runs) == 0

    def test_two_buckets(self):
        es_response = {'aggregations': {'by_run': {'buckets': [
            {'key': 'run-1', 'doc_count': 565, 'file_count': {'value': 50},
             'bytes_total': {'value': 64193}},
            {'key': 'run-2', 'doc_count': 7,   'file_count': {'value': 5},
             'bytes_total': {'value': 1971}},
        ]}}}
        reader = build_reader(response_queue=[_Fake_Response(200, json_body=es_response)])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        assert len(runs) == 2
        assert runs[0].event_count == 565
        assert runs[0].file_count  == 50
        assert runs[1].event_count == 7

    def test_404_returns_empty(self):                                               # No events indices → clean empty
        reader = build_reader(response_queue=[_Fake_Response(404, text='no such index')])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        assert len(runs) == 0


# ─── health ──────────────────────────────────────────────────────────────────

def status_for(response, name: str) -> str:
    for chk in response.checks:
        if str(chk.name) == name:
            return str(chk.status)
    return 'absent'


class test_Events__Read__health(TestCase):

    def test_all_present_returns_OK_rollup(self):                                   # All 4 checks pass
        # response_queue: 2 calls for inventory_processed_counts (total + processed)
        reader   = build_reader(fixture_count_response=(3, 200, ''),                # 3 events indices
                                  response_queue=[_Fake_Response(200, json_body={'count': 425}),  # total inventory
                                                   _Fake_Response(200, json_body={'count': 100})]) # processed
        response = reader.health(base_url='https://x', username='u', password='p',
                                  stack_name='elastic-fierce-faraday')
        assert response.all_ok is True
        assert len(response.checks) == 4
        assert status_for(response, 'events-indices')   == 'ok'
        assert status_for(response, 'events-data-view') == 'ok'
        assert status_for(response, 'events-dashboard') == 'ok'
        assert status_for(response, 'inventory-link')   == 'ok'

    def test_no_events_indices_warns(self):
        reader   = build_reader(fixture_count_response=(0, 200, ''),
                                  response_queue=[_Fake_Response(200, json_body={'count': 425}),
                                                   _Fake_Response(200, json_body={'count': 0})])
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is True                                                # WARN doesn't flip rollup
        assert status_for(response, 'events-indices') == 'warn'

    def test_indices_error_fails_rollup(self):
        reader   = build_reader(fixture_count_response=(0, 503, 'cluster red'),
                                  response_queue=[_Fake_Response(200, json_body={'count': 0}),
                                                   _Fake_Response(200, json_body={'count': 0})])
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is False
        assert status_for(response, 'events-indices') == 'fail'

    def test_missing_dashboard_warns(self):
        reader   = build_reader(fixture_count_response=(1, 200, ''),
                                  dashboard_present=False,
                                  response_queue=[_Fake_Response(200, json_body={'count': 425}),
                                                   _Fake_Response(200, json_body={'count': 100})])
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is True
        assert status_for(response, 'events-dashboard') == 'warn'

    def test_inventory_link_no_inventory_warns(self):                               # When inventory has 0 docs total, link check WARNs
        reader   = build_reader(fixture_count_response=(1, 200, ''),
                                  response_queue=[_Fake_Response(200, json_body={'count': 0}),    # total=0
                                                   _Fake_Response(200, json_body={'count': 0})])  # processed=0
        response = reader.health(base_url='https://x', username='u', password='p')
        assert status_for(response, 'inventory-link') == 'warn'

    def test_inventory_link_partial_coverage(self):                                 # 100 of 425 docs processed → 24% (rounded)
        reader   = build_reader(fixture_count_response=(1, 200, ''),
                                  response_queue=[_Fake_Response(200, json_body={'count': 425}),
                                                   _Fake_Response(200, json_body={'count': 100})])
        response = reader.health(base_url='https://x', username='u', password='p')
        assert status_for(response, 'inventory-link') == 'ok'
        # Find the inventory-link detail
        for chk in response.checks:
            if str(chk.name) == 'inventory-link':
                assert '100 of 425' in str(chk.detail)
                assert '24%' in str(chk.detail)

    def test_check_order(self):                                                     # Stable order so the CLI table is consistent
        reader   = build_reader(fixture_count_response=(1, 200, ''),
                                  response_queue=[_Fake_Response(200, json_body={'count': 1}),
                                                   _Fake_Response(200, json_body={'count': 1})])
        response = reader.health(base_url='https://x', username='u', password='p')
        names    = [str(chk.name) for chk in response.checks]
        assert names == ['events-indices', 'events-data-view', 'events-dashboard', 'inventory-link']
