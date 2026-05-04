# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Manifest__Builder
# Verifies that build() returns a correctly-populated Schema__Consolidated__Manifest
# with every field, including defaults.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Manifest__Builder      import Manifest__Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidated__Manifest import Schema__Consolidated__Manifest


class test_Manifest__Builder(TestCase):

    def setUp(self):
        self.builder = Manifest__Builder()

    def _build(self, **overrides):
        defaults = dict(
            run_id                 = 'run-001'                    ,
            date_iso               = '2026-04-25'                 ,
            source_count           = 21                           ,
            event_count            = 150                          ,
            bucket                 = 'my-logs-bucket'             ,
            s3_output_key          = 'lets/raw-cf-to-consolidated/2026/04/25/events.ndjson.gz' ,
            bytes_written          = 98304                        ,
            parser_version         = '1.0.0'                      ,
            bot_classifier_version = '2.1.0'                      ,
            compat_region          = 'raw-cf-to-consolidated'     ,
            started_at             = '2026-04-25T10:00:00Z'       ,
            finished_at            = '2026-04-25T10:00:01Z'       ,
            consolidated_at        = '2026-04-25T10:00:00Z'       ,
        )
        defaults.update(overrides)
        return self.builder.build(**defaults)

    def test_returns_typed_manifest(self):
        m = self._build()
        assert isinstance(m, Schema__Consolidated__Manifest)

    def test_identity_fields(self):
        m = self._build(run_id='run-abc', date_iso='2026-04-25')
        assert str(m.run_id)   == 'run-abc'
        assert str(m.date_iso) == '2026-04-25'

    def test_count_fields(self):
        m = self._build(source_count=21, event_count=150)
        assert m.source_count == 21
        assert m.event_count  == 150

    def test_output_location(self):
        key = 'lets/raw-cf-to-consolidated/2026/04/25/events.ndjson.gz'
        m   = self._build(bucket='my-logs-bucket', s3_output_key=key, bytes_written=98304)
        assert str(m.bucket)        == 'my-logs-bucket'
        assert str(m.s3_output_key) == key
        assert m.bytes_written      == 98304

    def test_version_stamps(self):
        m = self._build(parser_version='1.0.0', bot_classifier_version='2.1.0',
                        compat_region='raw-cf-to-consolidated')
        assert str(m.parser_version)         == '1.0.0'
        assert str(m.bot_classifier_version) == '2.1.0'
        assert str(m.compat_region)          == 'raw-cf-to-consolidated'

    def test_timing_fields(self):
        m = self._build(started_at='2026-04-25T10:00:00Z',
                        finished_at='2026-04-25T10:00:01Z',
                        consolidated_at='2026-04-25T10:00:00Z')
        assert str(m.started_at)      == '2026-04-25T10:00:00Z'
        assert str(m.finished_at)     == '2026-04-25T10:00:01Z'
        assert str(m.consolidated_at) == '2026-04-25T10:00:00Z'

    def test_default_schema_version(self):
        m = self._build()
        assert str(m.schema_version) == 'Schema__Consolidated__Manifest_v1'

    def test_json_roundtrip(self):
        m = self._build()
        d = m.json()
        assert d['source_count'] == 21
        assert d['event_count']  == 150
        assert 'schema_version'  in d
