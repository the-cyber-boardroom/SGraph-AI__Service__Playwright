# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__SG_Send__Sync__Response
# Pins defaults and that nested sub-responses auto-instantiate correctly
# (no raw dicts — only Type_Safe schemas).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Response import Schema__Inventory__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Response       import Schema__Events__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Response     import Schema__SG_Send__Sync__Response


class test_Schema__SG_Send__Sync__Response(TestCase):

    def test_defaults(self):
        resp = Schema__SG_Send__Sync__Response()
        assert str(resp.sync_date)      == ''
        assert resp.s3_calls_total      == 0
        assert resp.elastic_calls_total == 0
        assert resp.wall_ms             == 0
        assert resp.dry_run             is False

    def test_nested_responses_auto_instantiate(self):
        resp = Schema__SG_Send__Sync__Response()
        assert isinstance(resp.inventory_response, Schema__Inventory__Load__Response)
        assert isinstance(resp.events_response,    Schema__Events__Load__Response)

    def test_nested_response_fields_accessible(self):
        resp = Schema__SG_Send__Sync__Response()
        assert resp.inventory_response.objects_indexed  == 0
        assert resp.events_response.events_indexed      == 0

    def test_counter_totals_surfaced(self):
        resp = Schema__SG_Send__Sync__Response(s3_calls_total=5, elastic_calls_total=12)
        assert resp.s3_calls_total      == 5
        assert resp.elastic_calls_total == 12
