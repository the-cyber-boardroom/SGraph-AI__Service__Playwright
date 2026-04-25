# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__S3__Object__Record
# Pins the indexed-doc shape: default construction, populated construction,
# JSON round-trip, and the slice-2 hooks (content_processed defaults False).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__S3__Storage_Class    import Enum__S3__Storage_Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__S3__Object__Record import Schema__S3__Object__Record


class test_Schema__S3__Object__Record(TestCase):

    def test_default_construction(self):                                            # All fields present and zero-valued
        rec = Schema__S3__Object__Record()
        assert rec.bucket            == ''
        assert rec.key               == ''
        assert rec.size_bytes        == 0
        assert rec.etag              == ''
        assert rec.storage_class     == Enum__S3__Storage_Class.UNKNOWN
        assert rec.source            == Enum__LETS__Source__Slug.UNKNOWN
        assert rec.delivery_year     == 0
        assert rec.firehose_lag_ms   == 0
        assert rec.content_processed is False

    def test_with_values(self):
        rec = Schema__S3__Object__Record(bucket          = '745506449035--sgraph-send-cf-logs--eu-west-2',
                                          key             = 'cloudfront-realtime/2026/04/25/file.gz'      ,
                                          size_bytes      = 386                                            ,
                                          etag            = 'e71885f47b8c4d4fa930e1c6e7083682'              ,
                                          storage_class   = Enum__S3__Storage_Class.STANDARD               ,
                                          source          = Enum__LETS__Source__Slug.CF_REALTIME           ,
                                          delivery_year   = 2026                                            ,
                                          delivery_month  = 4                                               ,
                                          delivery_day    = 25                                              )
        assert rec.size_bytes     == 386
        assert rec.delivery_year  == 2026
        assert rec.storage_class  == Enum__S3__Storage_Class.STANDARD

    def test_json_roundtrip_keys(self):                                             # All 19 fields appear in .json() output
        keys = set(Schema__S3__Object__Record().json().keys())
        expected = {'bucket', 'key', 'last_modified', 'size_bytes', 'etag', 'storage_class',
                    'source', 'delivery_year', 'delivery_month', 'delivery_day',
                    'delivery_hour', 'delivery_minute', 'delivery_at', 'firehose_lag_ms',
                    'pipeline_run_id', 'loaded_at', 'schema_version',
                    'content_processed', 'content_extract_run_id'}
        assert keys == expected

    def test_default_schema_version(self):                                          # The schema_version field carries its own version tag
        assert str(Schema__S3__Object__Record().schema_version) == 'Schema__S3__Object__Record_v1'

    def test_content_processed_defaults_false(self):                                # Slice 2 flips this; slice 1 always emits False
        assert Schema__S3__Object__Record().content_processed is False
