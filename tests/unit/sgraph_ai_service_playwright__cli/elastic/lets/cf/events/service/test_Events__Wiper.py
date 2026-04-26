# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Events__Wiper
# End-to-end tests using the in-memory subclasses.  Pins:
#   - the four-step wipe order (indices → data view → saved objects →
#     inventory manifest reset)
#   - idempotency (second wipe returns all-zeros)
#   - inventory_reset_count is propagated from manifest_updater
#   - error from any step propagates to error_message but does NOT abort
#     the remaining steps
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Wiper import Events__Wiper

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater__In_Memory import Inventory__Manifest__Updater__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory   import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory                import Kibana__Saved_Objects__Client__In_Memory


def build_wiper(http_delete_response       : tuple = ()  ,
                kibana_view_existed        : bool  = True,
                kibana_objects_deleted     : int   = 0   ,
                manifest_reset_count       : int   = 0   ) -> Events__Wiper:
    http = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=(),
                                                delete_pattern_calls=[],
                                                fixture_delete_pattern_response=http_delete_response,
                                                count_pattern_calls=[], fixture_count_response=(),
                                                aggregate_calls=[], fixture_run_buckets=[])
    kb   = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                     dashboard_calls=[], harden_calls=[],
                                                     delete_object_calls=[], import_calls=[],
                                                     find_calls=[], fixture_find_objects={},
                                                     fixture_view_existed_for_delete=kibana_view_existed,
                                                     fixture_delete_object_count=kibana_objects_deleted)
    upd  = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[],
                                                    fixture_reset_count=manifest_reset_count)
    return Events__Wiper(http_client=http, kibana_client=kb, manifest_updater=upd)


class test_Events__Wiper(TestCase):

    def test_first_wipe_drops_everything_and_resets_manifest(self):
        wiper = build_wiper(http_delete_response   = (3, 200, ''),                  # 3 events indices
                             kibana_view_existed    = True       ,
                             kibana_objects_deleted = 7          ,                  # Dashboard + 6 visualizations
                             manifest_reset_count   = 425        )                  # Inventory had 425 docs flagged content_processed=true
        resp  = wiper.wipe(base_url='https://x', username='u', password='p',
                            stack_name='elastic-fierce-faraday')
        assert resp.indices_dropped       == 3
        assert resp.data_views_dropped    == 1
        assert resp.saved_objects_dropped == 7
        assert resp.inventory_reset_count == 425
        assert resp.error_message         == ''

    def test_idempotency_second_wipe_is_zeros(self):                                # No indices, no views, no flags — wipe-twice contract
        wiper = build_wiper(http_delete_response   = (0, 200, ''),
                             kibana_view_existed    = False      ,
                             kibana_objects_deleted = 0          ,
                             manifest_reset_count   = 0          )
        resp  = wiper.wipe(base_url='https://x', username='u', password='p')
        assert resp.indices_dropped       == 0
        assert resp.data_views_dropped    == 0
        assert resp.saved_objects_dropped == 0
        assert resp.inventory_reset_count == 0
        assert resp.error_message         == ''

    def test_index_pattern_is_events_wildcard(self):                                # Confirms we touch sg-cf-events-* (NOT sg-cf-inventory-*)
        wiper = build_wiper()
        wiper.wipe(base_url='https://x', username='u', password='p')
        assert wiper.http_client.delete_pattern_calls == [('https://x', 'sg-cf-events-*')]

    def test_data_view_title_is_events_wildcard(self):
        wiper = build_wiper()
        wiper.wipe(base_url='https://x', username='u', password='p')
        titles_called = [call[1] for call in wiper.kibana_client.delete_calls]
        assert 'sg-cf-events-*' in titles_called

    def test_dashboard_objects_are_seven_events_refs(self):                         # 1 dashboard + 6 visualizations from CF__Events__Dashboard__Ids
        wiper = build_wiper(kibana_objects_deleted=7)
        wiper.wipe(base_url='https://x', username='u', password='p')
        assert len(wiper.kibana_client.delete_object_calls) == 1
        base_url, refs = wiper.kibana_client.delete_object_calls[0]
        assert len(refs) == 7

    def test_manifest_reset_called_with_correct_url(self):                          # The manifest reset is the slice-2-specific final step
        wiper = build_wiper()
        wiper.wipe(base_url='https://x', username='u', password='p')
        assert wiper.manifest_updater.reset_calls == [('https://x',)]

    def test_index_delete_error_propagates_but_does_not_abort_loop(self):           # Errors are surfaced but every step still runs
        wiper = build_wiper(http_delete_response=(0, 503, 'cluster red'))
        resp  = wiper.wipe(base_url='https://x', username='u', password='p')
        assert 'cluster red' in resp.error_message
        # Subsequent steps still ran:
        assert wiper.kibana_client.delete_calls          != []
        assert wiper.kibana_client.delete_object_calls   != []
        assert wiper.manifest_updater.reset_calls        != []

    def test_duration_ms_populated(self):
        wiper = build_wiper()
        resp  = wiper.wipe(base_url='https://x', username='u', password='p')
        assert resp.duration_ms >= 0
