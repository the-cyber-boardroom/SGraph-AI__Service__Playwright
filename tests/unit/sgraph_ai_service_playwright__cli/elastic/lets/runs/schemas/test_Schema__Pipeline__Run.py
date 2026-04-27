# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Pipeline__Run
# Pins shape + defaults + JSON serialisability of the journal record.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.runs.enums.Enum__Pipeline__Verb              import Enum__Pipeline__Verb
from sgraph_ai_service_playwright__cli.elastic.lets.runs.schemas.Schema__Pipeline__Run            import Schema__Pipeline__Run
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.enums.Enum__LETS__Source__Slug   import Enum__LETS__Source__Slug


class test_Schema__Pipeline__Run(TestCase):

    def test_default_construction(self):
        record = Schema__Pipeline__Run()
        assert str(record.run_id)        == ''
        assert record.source             == Enum__LETS__Source__Slug.UNKNOWN
        assert record.verb               == Enum__Pipeline__Verb.UNKNOWN
        assert str(record.stack_name)    == ''
        assert record.dry_run            is False
        assert record.files_queued       == 0
        assert record.s3_calls           == 0
        assert record.elastic_calls      == 0
        assert record.last_http_status   == 0
        assert str(record.error_message) == ''
        assert str(record.schema_version) == 'Schema__Pipeline__Run_v1'

    def test_explicit_construction(self):
        record = Schema__Pipeline__Run(run_id        ='run-1'                              ,
                                        source        =Enum__LETS__Source__Slug.CF_REALTIME ,
                                        verb          =Enum__Pipeline__Verb.EVENTS_LOAD     ,
                                        files_queued  =50                                   ,
                                        files_processed=48                                  ,
                                        events_indexed=1234                                  ,
                                        s3_calls      =50                                   ,
                                        elastic_calls =60                                   ,
                                        started_at    ='2026-04-27T10:00:00Z'               ,
                                        finished_at   ='2026-04-27T10:00:42Z'               ,
                                        duration_ms   =42000                                )
        assert str(record.run_id)     == 'run-1'
        assert record.verb            == Enum__Pipeline__Verb.EVENTS_LOAD
        assert record.s3_calls        == 50
        assert record.elastic_calls   == 60
        assert record.duration_ms     == 42000

    def test_json_round_trip_includes_all_fields(self):                              # The tracker bulk-posts via doc.json() — every field must serialise
        record = Schema__Pipeline__Run(run_id    ='run-1'                          ,
                                        verb      =Enum__Pipeline__Verb.INVENTORY_LOAD)
        payload = record.json()
        assert payload['run_id']        == 'run-1'
        assert payload['verb']          == 'inventory-load'
        assert payload['s3_calls']      == 0
        assert payload['elastic_calls'] == 0
        assert payload['schema_version'] == 'Schema__Pipeline__Run_v1'

    def test_verb_enum_string_value(self):
        assert str(Enum__Pipeline__Verb.INVENTORY_LOAD) == 'inventory-load'
        assert str(Enum__Pipeline__Verb.EVENTS_LOAD)    == 'events-load'
        assert str(Enum__Pipeline__Verb.SG_SEND_LOAD)   == 'sg-send-load'
