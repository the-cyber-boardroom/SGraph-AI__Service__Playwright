# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Inventory__Load__Response
# Pins the result shape returned by Inventory__Loader.load().
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Response import Schema__Inventory__Load__Response


class test_Schema__Inventory__Load__Response(TestCase):

    def test_default_construction(self):
        resp = Schema__Inventory__Load__Response()
        assert resp.objects_scanned == 0
        assert resp.objects_indexed == 0
        assert resp.objects_updated == 0
        assert resp.bytes_total     == 0
        assert resp.dry_run         is False
        assert resp.error_message   == ''

    def test_with_values(self):
        resp = Schema__Inventory__Load__Response(run_id          = 'test-run-1'      ,
                                                  bucket          = 'my-bucket'       ,
                                                  prefix_resolved = 'a/b/c/'          ,
                                                  pages_listed    = 1                  ,
                                                  objects_scanned = 375                ,
                                                  objects_indexed = 375                ,
                                                  bytes_total     = 145_000            ,
                                                  duration_ms     = 4_200              ,
                                                  last_http_status= 200                ,
                                                  kibana_url      = 'https://1.2.3.4/' )
        assert resp.objects_indexed  == 375
        assert resp.last_http_status == 200

    def test_json_roundtrip_keys(self):                                             # All declared fields present in JSON
        keys = set(Schema__Inventory__Load__Response().json().keys())
        for f in ('run_id', 'stack_name', 'bucket', 'prefix_resolved',
                  'pages_listed', 'objects_scanned', 'objects_indexed',
                  'objects_updated', 'bytes_total', 'started_at', 'finished_at',
                  'duration_ms', 'last_http_status', 'error_message',
                  'kibana_url', 'dry_run'):
            assert f in keys
