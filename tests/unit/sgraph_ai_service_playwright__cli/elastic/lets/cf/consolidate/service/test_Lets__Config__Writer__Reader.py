# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Lets__Config__Writer + Lets__Config__Reader
# Verifies:
#   - Writer produces valid UTF-8 JSON bytes from a Schema__Lets__Config
#   - Reader reconstructs the schema from those bytes
#   - check_compat() accepts matching regions and rejects mismatches
#   - Edge cases: empty bytes, malformed JSON, missing fields
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.enums.Enum__Lets__Workflow__Type import Enum__Lets__Workflow__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config    import Schema__Lets__Config
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Writer    import Lets__Config__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Reader    import Lets__Config__Reader


def make_config(**overrides) -> Schema__Lets__Config:
    defaults = dict(
        config_version         = '1'                        ,
        workflow_type          = Enum__Lets__Workflow__Type.CONSOLIDATE ,
        input_type             = 's3'                       ,
        input_bucket           = 'my-logs-bucket'           ,
        input_prefix           = 'cloudfront-realtime/'     ,
        input_format           = 'cf-realtime-tsv-gz'       ,
        output_type            = 'ndjson-gz'                ,
        output_schema          = 'Schema__CF__Event__Record' ,
        output_schema_version  = 'v1'                       ,
        output_compression     = 'gzip'                     ,
        parser                 = 'CF__Realtime__Log__Parser' ,
        parser_version         = '1.0.0'                    ,
        bot_classifier         = 'Bot__Classifier'          ,
        bot_classifier_version = '2.1.0'                    ,
        consolidator           = 'Consolidate__Loader'      ,
        consolidator_version   = '0.1.100'                  ,
        created_at             = '2026-04-25T10:00:00Z'     ,
        created_by             = 'sp el lets cf consolidate load (run run-001)' ,
    )
    defaults.update(overrides)
    return Schema__Lets__Config(**defaults)


class test_Lets__Config__Writer__Reader(TestCase):

    def setUp(self):
        self.writer = Lets__Config__Writer()
        self.reader = Lets__Config__Reader()

    # ─── Writer ───────────────────────────────────────────────────────────────

    def test_writer_produces_bytes(self):
        data = self.writer.to_bytes(make_config())
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_writer_produces_valid_json(self):
        data = self.writer.to_bytes(make_config())
        d    = json.loads(data.decode('utf-8'))
        assert d['config_version']    == '1'
        assert d['workflow_type']     == 'consolidate'
        assert d['parser_version']    == '1.0.0'
        assert d['output_schema']     == 'Schema__CF__Event__Record'

    def test_writer_pretty_prints(self):                                            # Human-readable, sorted keys
        data = self.writer.to_bytes(make_config())
        text = data.decode('utf-8')
        assert '\n' in text                                                          # Indented
        assert 'bot_classifier' in text                                             # Sorted keys ensure predictable order

    # ─── Reader ───────────────────────────────────────────────────────────────

    def test_reader_roundtrip(self):
        original = make_config()
        data     = self.writer.to_bytes(original)
        restored, err = self.reader.from_bytes(data)
        assert err == ''
        assert str(restored.parser_version)    == '1.0.0'
        assert str(restored.output_schema)     == 'Schema__CF__Event__Record'
        assert restored.workflow_type          == Enum__Lets__Workflow__Type.CONSOLIDATE

    def test_reader_empty_bytes_returns_error(self):
        config, err = self.reader.from_bytes(b'')
        assert err != ''
        assert isinstance(config, Schema__Lets__Config)

    def test_reader_malformed_json_returns_error(self):
        config, err = self.reader.from_bytes(b'{not valid json}')
        assert err != ''

    def test_reader_unknown_extra_fields_handled(self):                             # Extra fields in S3 JSON should not crash
        d    = make_config().json()
        d['future_field'] = 'some-value'                                            # Simulate a future version writing an extra field
        data = json.dumps(d).encode('utf-8')
        config, err = self.reader.from_bytes(data)
        # Either parsed OK or returned an error — must not raise
        assert isinstance(config, Schema__Lets__Config)

    # ─── check_compat ─────────────────────────────────────────────────────────

    def test_compat_same_config_passes(self):
        cfg = make_config()
        err = self.reader.check_compat(cfg, cfg)
        assert err == ''

    def test_compat_parser_version_mismatch_rejected(self):
        stored  = make_config(parser_version='1.0.0')
        current = make_config(parser_version='2.0.0')
        err = self.reader.check_compat(stored, current)
        assert 'parser_version' in err
        assert '1.0.0' in err
        assert '2.0.0' in err

    def test_compat_output_schema_mismatch_rejected(self):
        stored  = make_config(output_schema='Schema__CF__Event__Record')
        current = make_config(output_schema='Schema__CF__Event__Record__V2')
        err = self.reader.check_compat(stored, current)
        assert 'output_schema' in err

    def test_compat_output_schema_version_mismatch_rejected(self):
        stored  = make_config(output_schema_version='v1')
        current = make_config(output_schema_version='v2')
        err = self.reader.check_compat(stored, current)
        assert 'output_schema_version' in err

    def test_compat_empty_current_field_not_rejected(self):                         # If current tool has no version stamped, don't reject (partial config)
        stored  = make_config(parser_version='1.0.0')
        current = make_config(parser_version='')
        err = self.reader.check_compat(stored, current)
        assert err == ''                                                             # Both must be populated to compare

    def test_compat_multiple_mismatches_all_reported(self):
        stored  = make_config(parser_version='1.0.0', output_schema_version='v1')
        current = make_config(parser_version='2.0.0', output_schema_version='v2')
        err = self.reader.check_compat(stored, current)
        assert 'parser_version'        in err
        assert 'output_schema_version' in err
