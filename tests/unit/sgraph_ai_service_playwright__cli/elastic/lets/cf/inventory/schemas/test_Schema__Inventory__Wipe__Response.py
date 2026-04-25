# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Inventory__Wipe__Response
# Pins the result shape Inventory__Wiper.wipe() returns. A second wipe should
# return all-zeros — that's the idempotency contract we'll assert in Phase 4.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Wipe__Response import Schema__Inventory__Wipe__Response


class test_Schema__Inventory__Wipe__Response(TestCase):

    def test_default_construction_is_zero(self):                                    # Default == "no-op wipe" shape
        resp = Schema__Inventory__Wipe__Response()
        assert resp.indices_dropped       == 0
        assert resp.data_views_dropped    == 0
        assert resp.saved_objects_dropped == 0
        assert resp.duration_ms           == 0
        assert resp.error_message         == ''

    def test_with_values(self):
        resp = Schema__Inventory__Wipe__Response(stack_name           = 'elastic-fierce-faraday',
                                                  indices_dropped      = 3                       ,
                                                  data_views_dropped   = 1                       ,
                                                  saved_objects_dropped= 5                       ,
                                                  duration_ms          = 850                     )
        assert resp.indices_dropped == 3
        assert resp.duration_ms     == 850
