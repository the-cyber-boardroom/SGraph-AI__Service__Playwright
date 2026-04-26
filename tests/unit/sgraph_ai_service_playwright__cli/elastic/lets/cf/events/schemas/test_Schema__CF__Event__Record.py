# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__CF__Event__Record
# Pins the indexed-doc shape: 37 fields total, group-by-group construction,
# JSON round-trip, and the standard pipeline-metadata defaults.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category       import Enum__CF__Bot__Category
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Edge__Result__Type  import Enum__CF__Edge__Result__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method              import Enum__CF__Method
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class       import Enum__CF__Status__Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record import Schema__CF__Event__Record


class test_Schema__CF__Event__Record(TestCase):

    def test_default_construction_matches_sentinels(self):                          # Defensive defaults — "-1 = no origin call", "OTHER" enums
        rec = Schema__CF__Event__Record()
        assert rec.sc_status         == 0
        assert rec.sc_bytes          == 0
        assert rec.cs_method         == Enum__CF__Method.OTHER
        assert rec.x_edge_result_type == Enum__CF__Edge__Result__Type.Other
        assert rec.sc_status_class   == Enum__CF__Status__Class.OTHER
        assert rec.bot_category      == Enum__CF__Bot__Category.UNKNOWN
        assert rec.is_bot            is False
        assert rec.cache_hit         is False
        assert rec.sc_range_start    == -1                                          # "-" from TSV → -1
        assert rec.sc_range_end      == -1
        assert rec.origin_fbl_ms     == -1
        assert rec.origin_lbl_ms     == -1
        assert rec.line_index        == 0

    def test_full_field_count_in_json(self):                                        # 38 fields = 26 TSV + 4 derived + 5 lineage (incl. doc_id) + 3 pipeline
        keys = set(Schema__CF__Event__Record().json().keys())
        assert len(keys) == 38

    def test_doc_id_default_empty(self):                                            # doc_id is stamped by Events__Loader after parsing — empty in the parser output
        assert str(Schema__CF__Event__Record().doc_id) == ''

    def test_default_schema_version(self):
        assert str(Schema__CF__Event__Record().schema_version) == 'Schema__CF__Event__Record_v1'

    def test_with_real_log_values(self):                                            # Build from the user's pasted CF log line 1 (the wpbot 302)
        rec = Schema__CF__Event__Record(timestamp           = '2026-04-21T12:00:17Z'                                       ,
                                          time_taken_ms       = 1                                                            ,
                                          sc_status           = 302                                                          ,
                                          sc_bytes            = 246                                                          ,
                                          cs_method           = Enum__CF__Method.GET                                          ,
                                          cs_host             = 'sgraph.ai'                                                  ,
                                          cs_uri_stem         = '/enhancecp'                                                 ,
                                          x_edge_location     = 'HIO52-P4'                                                   ,
                                          x_edge_request_id   = '2TZI-f7L0PmDR-76lAEx4wdq-StamTTbisIdbMSYhB4eVeyTcPy0qw=='  ,
                                          ttfb_ms             = 1                                                            ,
                                          x_edge_result_type  = Enum__CF__Edge__Result__Type.FunctionGeneratedResponse        ,
                                          c_country           = 'US'                                                         ,
                                          source_etag         = 'e71885f47b8c4d4fa930e1c6e7083682'                            ,
                                          line_index          = 0                                                            )
        assert rec.sc_status         == 302
        assert rec.x_edge_result_type == Enum__CF__Edge__Result__Type.FunctionGeneratedResponse
        assert str(rec.cs_uri_stem)  == '/enhancecp'
        assert str(rec.c_country)    == 'US'
