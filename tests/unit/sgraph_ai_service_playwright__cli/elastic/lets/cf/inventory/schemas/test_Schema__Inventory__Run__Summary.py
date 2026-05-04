# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Inventory__Run__Summary
# Pins the per-run summary shape produced by Inventory__Read.list().
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Run__Summary import Schema__Inventory__Run__Summary


class test_Schema__Inventory__Run__Summary(TestCase):

    def test_default_construction(self):
        s = Schema__Inventory__Run__Summary()
        assert s.pipeline_run_id   == ''
        assert s.object_count      == 0
        assert s.bytes_total       == 0
        assert s.earliest_loaded   == ''
        assert s.latest_loaded     == ''

    def test_with_values(self):
        s = Schema__Inventory__Run__Summary(pipeline_run_id   = 'run-1' ,
                                             object_count      = 375     ,
                                             bytes_total       = 145_000 ,
                                             earliest_loaded   = '2026-04-25T10:30:00Z',
                                             latest_loaded     = '2026-04-25T10:30:05Z',
                                             earliest_delivery = '2026-04-25T00:00:20Z',
                                             latest_delivery   = '2026-04-25T23:59:50Z')
        assert s.object_count == 375
        assert s.latest_delivery == '2026-04-25T23:59:50Z'
