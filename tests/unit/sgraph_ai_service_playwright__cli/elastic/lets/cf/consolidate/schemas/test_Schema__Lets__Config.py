# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Lets__Config
# Pins default construction, populated construction, and JSON round-trip keys.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.enums.Enum__Lets__Workflow__Type  import Enum__Lets__Workflow__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config      import Schema__Lets__Config


class test_Schema__Lets__Config(TestCase):

    def test_default_construction(self):
        cfg = Schema__Lets__Config()
        assert str(cfg.config_version) == '1'
        assert cfg.workflow_type       == Enum__Lets__Workflow__Type.UNKNOWN
        assert str(cfg.input_bucket)   == ''
        assert str(cfg.parser)         == ''
        assert str(cfg.created_at)     == ''

    def test_with_values(self):
        cfg = Schema__Lets__Config(
            workflow_type          = Enum__Lets__Workflow__Type.CONSOLIDATE          ,
            input_bucket           = '745506449035--sgraph-send-cf-logs--eu-west-2'  ,
            input_prefix           = 'cloudfront-realtime/'                          ,
            input_format           = 'cf-realtime-tsv-gz'                            ,
            output_type            = 'ndjson-gz'                                     ,
            output_schema          = 'Schema__CF__Event__Record'                     ,
            output_schema_version  = 'v1'                                            ,
            output_compression     = 'gzip'                                          ,
            parser                 = 'CF__Realtime__Log__Parser'                     ,
            parser_version         = 'v0.1.100'                                      ,
            bot_classifier         = 'Bot__Classifier'                               ,
            bot_classifier_version = 'v0.1.100'                                      ,
            consolidator           = 'Consolidate__Loader'                           ,
            consolidator_version   = 'v0.1.101'                                      ,
            created_at             = '2026-04-27T03:00:00Z'                          ,
            created_by             = 'sp el lets cf consolidate load (run test-001)' ,
        )
        assert cfg.workflow_type          == Enum__Lets__Workflow__Type.CONSOLIDATE
        assert str(cfg.input_bucket)      == '745506449035--sgraph-send-cf-logs--eu-west-2'
        assert str(cfg.parser_version)    == 'v0.1.100'
        assert str(cfg.consolidator)      == 'Consolidate__Loader'

    def test_json_roundtrip_keys(self):
        keys = set(Schema__Lets__Config().json().keys())
        expected = {'config_version', 'workflow_type',
                    'input_type', 'input_bucket', 'input_prefix', 'input_format',
                    'output_type', 'output_schema', 'output_schema_version', 'output_compression',
                    'parser', 'parser_version', 'bot_classifier', 'bot_classifier_version',
                    'consolidator', 'consolidator_version',
                    'created_at', 'created_by'}
        assert keys == expected
