# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Consolidate__Load__Response
# Pins defaults and JSON round-trip keys.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidate__Load__Response import Schema__Consolidate__Load__Response


class test_Schema__Consolidate__Load__Response(TestCase):

    def test_default_construction(self):
        resp = Schema__Consolidate__Load__Response()
        assert str(resp.run_id)           == ''
        assert resp.files_queued          == 0
        assert resp.files_processed       == 0
        assert resp.events_consolidated   == 0
        assert resp.bytes_written         == 0
        assert resp.inventory_updated     == 0
        assert resp.last_http_status      == 0
        assert str(resp.error_message)    == ''
        assert resp.dry_run               is False

    def test_json_roundtrip_keys(self):
        keys = set(Schema__Consolidate__Load__Response().json().keys())
        expected = {'run_id', 'stack_name', 'date_iso', 'bucket', 'compat_region',
                    'queue_mode', 'files_queued', 'files_processed', 'files_skipped',
                    'events_consolidated', 'bytes_total', 'bytes_written',
                    'inventory_updated', 's3_output_key',
                    'started_at', 'finished_at', 'duration_ms',
                    'last_http_status', 'error_message', 'dry_run'}
        assert keys == expected
