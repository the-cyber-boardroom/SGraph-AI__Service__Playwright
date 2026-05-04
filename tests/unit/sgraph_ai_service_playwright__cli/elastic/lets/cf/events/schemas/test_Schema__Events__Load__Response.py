# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Events__Load__Response
# Result of `events load` — per-file + aggregate counts.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Response import Schema__Events__Load__Response


class test_Schema__Events__Load__Response(TestCase):

    def test_default_construction(self):
        resp = Schema__Events__Load__Response()
        assert resp.files_queued      == 0
        assert resp.files_processed   == 0
        assert resp.files_skipped     == 0
        assert resp.events_indexed    == 0
        assert resp.events_updated    == 0
        assert resp.bytes_total       == 0
        assert resp.inventory_updated == 0
        assert resp.dry_run           is False
        assert resp.error_message     == ''

    def test_with_values(self):
        resp = Schema__Events__Load__Response(run_id            = 'test-run-1'      ,
                                                queue_mode        = 'from-inventory' ,
                                                files_queued      = 50               ,
                                                files_processed   = 50               ,
                                                events_indexed    = 5_000            ,
                                                events_updated    = 0                ,
                                                bytes_total       = 75_000           ,
                                                inventory_updated = 50               ,
                                                last_http_status  = 200              ,
                                                kibana_url        = 'https://1.2.3.4/')
        assert resp.events_indexed    == 5_000
        assert resp.queue_mode        == 'from-inventory'
        assert resp.inventory_updated == 50
        assert resp.last_http_status  == 200

    def test_json_roundtrip_keys(self):
        keys = set(Schema__Events__Load__Response().json().keys())
        for f in ('run_id', 'stack_name', 'bucket', 'prefix_resolved', 'queue_mode',
                  'files_queued', 'files_processed', 'files_skipped',
                  'events_indexed', 'events_updated', 'bytes_total',
                  'inventory_updated', 'started_at', 'finished_at',
                  'duration_ms', 'last_http_status', 'error_message',
                  'kibana_url', 'dry_run'):
            assert f in keys
