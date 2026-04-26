# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Read
# Pins list_runs() and health() against the in-memory subclasses. No mocks.
#
# list_runs:
#   - empty buckets → empty result
#   - real bucket shape → Schema__Inventory__Run__Summary fields parsed
#
# health:
#   - all-OK rollup
#   - missing data view → WARN (not FAIL) — load creates it idempotently
#   - missing dashboard → WARN (load imports it idempotently)
#   - indices error from HTTP layer → FAIL flips all_ok
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.CF__Inventory__Dashboard__Ids import DASHBOARD_ID
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Read import Inventory__Read

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory             import Kibana__Saved_Objects__Client__In_Memory


def build_reader(http_count_response : tuple = (1, 200, '')                       ,
                  http_buckets        : list  = None                              ,
                  data_view_present   : bool  = True                              ,
                  dashboard_present   : bool  = True                              ) -> Inventory__Read:
    http = Inventory__HTTP__Client__In_Memory(bulk_calls                       = [],
                                               fixture_response                 = (),
                                               delete_pattern_calls             = [],
                                               fixture_delete_pattern_response  = (),
                                               count_pattern_calls              = [],
                                               fixture_count_response           = http_count_response,
                                               aggregate_calls                  = [],
                                               fixture_run_buckets              = list(http_buckets or []))
    fixture_find = {}
    if data_view_present:
        fixture_find['index-pattern'] = [{'id': 'dv-uuid-1', 'type': 'index-pattern',
                                            'title': 'sg-cf-inventory-*', 'updated_at': '2026-04-26T11:00:00Z'}]
    if dashboard_present:
        fixture_find['dashboard'] = [{'id': DASHBOARD_ID, 'type': 'dashboard',
                                        'title': 'CloudFront Logs - Inventory Overview', 'updated_at': '2026-04-26T11:00:00Z'}]
    kb = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                   dashboard_calls=[], harden_calls=[],
                                                   delete_object_calls=[], import_calls=[],
                                                   find_calls=[],
                                                   fixture_find_objects=fixture_find)
    return Inventory__Read(http_client=http, kibana_client=kb)


# ─── list_runs ───────────────────────────────────────────────────────────────

class test_Inventory__Read__list_runs(TestCase):

    def test_empty_buckets_returns_empty_list(self):
        reader = build_reader(http_buckets=[])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        assert len(runs) == 0

    def test_single_bucket_parsed_into_run_summary(self):
        bucket = {
            'key'              : '20260426T103042Z-cf-realtime-load-a3f2',
            'doc_count'        : 425,
            'bytes_total'      : {'value': 633091.0},
            'earliest_loaded'  : {'value': 1, 'value_as_string': '2026-04-26T10:30:42.000Z'},
            'latest_loaded'    : {'value': 2, 'value_as_string': '2026-04-26T10:30:48.000Z'},
            'earliest_delivery': {'value': 3, 'value_as_string': '2026-04-25T00:00:20.000Z'},
            'latest_delivery'  : {'value': 4, 'value_as_string': '2026-04-25T23:59:50.000Z'},
        }
        reader = build_reader(http_buckets=[bucket])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        assert len(runs) == 1
        run = runs[0]
        assert str(run.pipeline_run_id) == '20260426T103042Z-cf-realtime-load-a3f2'
        assert run.object_count        == 425
        assert run.bytes_total         == 633_091
        assert str(run.earliest_delivery) == '2026-04-25T00:00:20.000Z'
        assert str(run.latest_delivery)   == '2026-04-25T23:59:50.000Z'

    def test_aggregate_called_with_correct_index_pattern(self):
        reader = build_reader(http_buckets=[])
        reader.list_runs(base_url='https://x', username='u', password='p', top_n=42)
        assert reader.http_client.aggregate_calls == [('https://x', 'sg-cf-inventory-*', 42)]

    def test_multiple_buckets_preserve_order(self):                                 # ES returns them in order; we don't reorder
        b1 = {'key': 'run-old', 'doc_count': 100, 'bytes_total': {'value': 1000}}
        b2 = {'key': 'run-new', 'doc_count': 200, 'bytes_total': {'value': 2000}}
        reader = build_reader(http_buckets=[b1, b2])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        assert [str(r.pipeline_run_id) for r in runs] == ['run-old', 'run-new']

    def test_missing_sub_aggs_default_to_zeros_and_empty_strings(self):             # Defensive: cluster might return partial buckets
        b = {'key': 'r1', 'doc_count': 5}                                            # No bytes_total / loaded / delivery aggs
        reader = build_reader(http_buckets=[b])
        runs   = reader.list_runs(base_url='https://x', username='u', password='p')
        run    = runs[0]
        assert run.bytes_total          == 0
        assert str(run.earliest_loaded) == ''
        assert str(run.latest_delivery) == ''


# ─── health ──────────────────────────────────────────────────────────────────

def status_for(response, name: str) -> str:                                         # Helper: look up a check's status by name in the response
    for chk in response.checks:
        if str(chk.name) == name:
            return str(chk.status)
    return 'absent'


class test_Inventory__Read__health(TestCase):

    def test_all_present_returns_OK_rollup(self):                                   # Indices + data view + dashboard all there
        reader   = build_reader()
        response = reader.health(base_url='https://x', username='u', password='p',
                                  stack_name='elastic-fierce-faraday')
        assert response.all_ok is True
        assert str(response.stack_name) == 'elastic-fierce-faraday'
        assert len(response.checks) == 3
        assert status_for(response, 'indices')   == 'ok'
        assert status_for(response, 'data-view') == 'ok'
        assert status_for(response, 'dashboard') == 'ok'

    def test_no_indices_warns_but_not_fails_rollup(self):                           # WARN doesn't flip all_ok
        reader   = build_reader(http_count_response=(0, 200, ''))
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is True                                                # WARN keeps the rollup OK-ish
        assert status_for(response, 'indices') == 'warn'

    def test_indices_error_fails_rollup(self):                                      # FAIL flips all_ok
        reader   = build_reader(http_count_response=(0, 503, 'cluster red'))
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is False
        assert status_for(response, 'indices') == 'fail'

    def test_missing_data_view_warns(self):
        reader   = build_reader(data_view_present=False)
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is True                                                # WARN, not FAIL
        assert status_for(response, 'data-view') == 'warn'

    def test_missing_dashboard_warns(self):
        reader   = build_reader(dashboard_present=False)
        response = reader.health(base_url='https://x', username='u', password='p')
        assert response.all_ok is True
        assert status_for(response, 'dashboard') == 'warn'

    def test_check_order_indices_data_view_dashboard(self):                         # Pin the order so the CLI table is stable
        reader   = build_reader()
        response = reader.health(base_url='https://x', username='u', password='p')
        names    = [str(chk.name) for chk in response.checks]
        assert names == ['indices', 'data-view', 'dashboard']
