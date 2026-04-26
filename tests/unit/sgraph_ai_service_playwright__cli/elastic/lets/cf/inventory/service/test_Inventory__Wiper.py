# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Wiper
# End-to-end tests using both *__In_Memory subclasses. Pins:
#   - the three-step wipe order (indices → data views → saved objects)
#   - idempotency: a second wipe on a clean stack returns all-zeros
#   - both legacy ("sg-cf-inventory") and current ("sg-cf-inventory-*")
#     data view titles are deleted defensively
#   - error from any step propagates to error_message but doesn't abort the
#     remaining steps
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Wiper import Inventory__Wiper

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory             import Kibana__Saved_Objects__Client__In_Memory


def build_wiper(http_delete_response       : tuple = ()  ,
                kibana_view_existed        : bool  = True,
                kibana_objects_deleted     : int   = 0   ) -> Inventory__Wiper:
    http = Inventory__HTTP__Client__In_Memory(bulk_calls                       = [],
                                               fixture_response                 = (),
                                               delete_pattern_calls             = [],
                                               fixture_delete_pattern_response  = http_delete_response)
    kb   = Kibana__Saved_Objects__Client__In_Memory(ensure_calls                    = [],
                                                     delete_calls                    = [],
                                                     dashboard_calls                 = [],
                                                     harden_calls                    = [],
                                                     delete_object_calls             = [],
                                                     fixture_view_existed_for_delete = kibana_view_existed,
                                                     fixture_delete_object_count     = kibana_objects_deleted)
    return Inventory__Wiper(http_client=http, kibana_client=kb)


class test_Inventory__Wiper(TestCase):

    def test_first_wipe_drops_everything(self):                                     # Counts from each step propagate to the response
        wiper = build_wiper(http_delete_response   = (3, 200, ''),                  # 3 indices matched & deleted
                             kibana_view_existed    = True       ,                  # Both legacy + current data views existed
                             kibana_objects_deleted = 5          )                  # 5 saved objects (dashboard + 4 visualisations)
        resp  = wiper.wipe(base_url='https://1.2.3.4', username='u', password='p',
                            stack_name='elastic-fierce-faraday')
        assert resp.indices_dropped       == 3
        assert resp.data_views_dropped    == 2                                      # current + legacy
        assert resp.saved_objects_dropped == 5
        assert resp.error_message         == ''
        assert resp.stack_name            == 'elastic-fierce-faraday'

    def test_idempotency_second_wipe_is_zeros(self):                                # Wipe → wipe must end in a zero state
        wiper = build_wiper(http_delete_response   = (0, 200, ''),                  # No indices left
                             kibana_view_existed    = False      ,                  # Both data views already gone
                             kibana_objects_deleted = 0          )                  # No saved objects
        resp  = wiper.wipe(base_url='https://x', username='u', password='p')
        assert resp.indices_dropped       == 0
        assert resp.data_views_dropped    == 0
        assert resp.saved_objects_dropped == 0
        assert resp.error_message         == ''

    def test_index_pattern_wildcard_is_used(self):                                  # The HTTP client receives the daily-rolling wildcard
        wiper = build_wiper(http_delete_response=(0, 200, ''))
        wiper.wipe(base_url='https://x', username='u', password='p')
        assert wiper.http_client.delete_pattern_calls == [('https://x', 'sg-cf-inventory-*')]

    def test_both_data_view_titles_attempted(self):                                 # Defensive: legacy "sg-cf-inventory" + current "sg-cf-inventory-*"
        wiper = build_wiper()
        wiper.wipe(base_url='https://x', username='u', password='p')
        titles_called = [call[1] for call in wiper.kibana_client.delete_calls]
        assert 'sg-cf-inventory-*' in titles_called
        assert 'sg-cf-inventory'   in titles_called

    def test_dashboard_objects_deleted_with_six_known_refs(self):                   # 1 dashboard + 5 visualisations from CF__Inventory__Dashboard__Ids
        wiper = build_wiper(kibana_objects_deleted=6)
        wiper.wipe(base_url='https://x', username='u', password='p')
        assert len(wiper.kibana_client.delete_object_calls) == 1
        base_url, refs = wiper.kibana_client.delete_object_calls[0]
        assert base_url == 'https://x'
        assert len(refs) == 6

    def test_index_delete_error_propagates_but_does_not_abort(self):                # Indices step fails but data views + saved objects still attempted
        wiper = build_wiper(http_delete_response=(0, 503, 'cluster red'))
        resp  = wiper.wipe(base_url='https://x', username='u', password='p')
        assert resp.indices_dropped == 0
        assert 'cluster red' in resp.error_message
        # The other two steps still ran:
        assert wiper.kibana_client.delete_calls          != []
        assert wiper.kibana_client.delete_object_calls   != []

    def test_duration_ms_populated(self):                                           # Sanity: response carries a non-negative duration
        wiper = build_wiper()
        resp  = wiper.wipe(base_url='https://x', username='u', password='p')
        assert resp.duration_ms >= 0
