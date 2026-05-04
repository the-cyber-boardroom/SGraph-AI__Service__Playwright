# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Consolidated__Manifest
# Pins default construction, populated construction, and JSON round-trip keys.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidated__Manifest import Schema__Consolidated__Manifest


class test_Schema__Consolidated__Manifest(TestCase):

    def test_default_construction(self):
        m = Schema__Consolidated__Manifest()
        assert str(m.run_id)          == ''
        assert str(m.date_iso)        == ''
        assert m.source_count         == 0
        assert m.event_count          == 0
        assert m.bytes_written        == 0
        assert str(m.s3_output_key)   == ''
        assert str(m.consolidated_at) == ''
        assert str(m.schema_version)  == 'Schema__Consolidated__Manifest_v1'

    def test_with_values(self):
        m = Schema__Consolidated__Manifest(
            run_id                 = 'cons-2026-04-27-abc123'                        ,
            date_iso               = '2026-04-27'                                    ,
            source_count           = 425                                             ,
            event_count            = 1500                                            ,
            bucket                 = '745506449035--sgraph-send-cf-logs--eu-west-2'  ,
            s3_output_key          = 'lets/raw-cf-to-consolidated/2026/04/27/events.ndjson.gz',
            bytes_written          = 204800                                          ,
            parser_version         = 'v0.1.100'                                      ,
            bot_classifier_version = 'v0.1.100'                                      ,
            compat_region          = 'raw-cf-to-consolidated'                        ,
            consolidated_at        = '2026-04-27T03:05:00Z'                         ,
            started_at             = '2026-04-27T03:00:00Z'                         ,
            finished_at            = '2026-04-27T03:05:00Z'                         ,
        )
        assert str(m.run_id)          == 'cons-2026-04-27-abc123'
        assert m.source_count         == 425
        assert m.event_count          == 1500
        assert str(m.parser_version)  == 'v0.1.100'

    def test_json_roundtrip_keys(self):
        keys = set(Schema__Consolidated__Manifest().json().keys())
        expected = {'run_id', 'date_iso', 'source_count', 'event_count',
                    'bucket', 's3_output_key', 'bytes_written',
                    'parser_version', 'bot_classifier_version', 'compat_region',
                    'consolidated_at', 'started_at', 'finished_at', 'schema_version'}
        assert keys == expected
