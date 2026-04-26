# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Events__Wipe__Response
# Tracks inventory_reset_count too — slice 2 wipe also resets the slice 1
# manifest's content_processed flags back to false.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Wipe__Response import Schema__Events__Wipe__Response


class test_Schema__Events__Wipe__Response(TestCase):

    def test_default_construction_is_zero(self):
        resp = Schema__Events__Wipe__Response()
        assert resp.indices_dropped       == 0
        assert resp.data_views_dropped    == 0
        assert resp.saved_objects_dropped == 0
        assert resp.inventory_reset_count == 0
        assert resp.duration_ms           == 0
        assert resp.error_message         == ''

    def test_with_values(self):
        resp = Schema__Events__Wipe__Response(stack_name             = 'elastic-fierce-faraday',
                                                indices_dropped        = 7                       ,
                                                data_views_dropped     = 1                       ,
                                                saved_objects_dropped  = 7                       ,
                                                inventory_reset_count  = 425                     ,
                                                duration_ms            = 3_400                   )
        assert resp.indices_dropped       == 7
        assert resp.inventory_reset_count == 425
