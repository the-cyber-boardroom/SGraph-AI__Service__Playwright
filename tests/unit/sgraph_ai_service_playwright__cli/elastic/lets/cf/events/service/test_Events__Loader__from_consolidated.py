# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Events__Loader --from-consolidated
# Pins the decision #8 fast path: reads events.ndjson.gz + manifest.json from
# S3, posts one bulk call (refresh=False, routing=date), then updates
# content_processed for all source inventory docs via a single terms query.
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Consolidate__Loader     import s3_key_for_config, s3_key_for_manifest, s3_key_for_events, _PARSER_VERSION
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Reader    import Lets__Config__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Writer    import Lets__Config__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Writer          import NDJSON__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Reader          import NDJSON__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record    import Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Request import Schema__Events__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Response import Schema__Events__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier              import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser    import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Loader               import Events__Loader

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader__In_Memory  import Inventory__Manifest__Reader__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater__In_Memory import Inventory__Manifest__Updater__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher__In_Memory          import S3__Object__Fetcher__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory   import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister__In_Memory     import S3__Inventory__Lister__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.test_Run__Id__Generator              import Deterministic__Run__Id__Generator
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker__In_Memory            import Pipeline__Runs__Tracker__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory                import Kibana__Saved_Objects__Client__In_Memory


DATE_ISO    = '2026-04-25'
BUCKET      = '745506449035--sgraph-send-cf-logs--eu-west-2'
COMPAT      = 'raw-cf-to-consolidated'
CONSOL_RUN  = '20260425T090000Z-cf-realtime-consolidate-load-bb01'
EVENTS_KEY  = s3_key_for_events(COMPAT, DATE_ISO)
MANIFEST_KEY = s3_key_for_manifest(COMPAT, DATE_ISO)
CONFIG_KEY  = s3_key_for_config(COMPAT)


SRC_ETAG = 'aabbccdd11223344aabbccdd11223344'                                       # 32-char hex — passes Safe_Str__S3__ETag validation


def _make_event_records(n: int = 3) -> List__Schema__CF__Event__Record:
    lst = List__Schema__CF__Event__Record()
    for i in range(n):
        lst.append(Schema__CF__Event__Record(
            sc_status   = 200 + i                     ,
            timestamp   = f'2026-04-25T10:0{i}:00Z'  ,
            doc_id      = f'{SRC_ETAG}__{i}'          ,
            source_etag = SRC_ETAG                    ,
        ))
    return lst


def _make_manifest(events_key: str = EVENTS_KEY) -> bytes:
    d = {'run_id'        : CONSOL_RUN   ,
          'date_iso'      : DATE_ISO     ,
          'source_count'  : 2            ,
          'event_count'   : 3            ,
          'bucket'        : BUCKET       ,
          's3_output_key' : events_key   ,
          'bytes_written' : 999          ,
          'schema_version': 'Schema__Consolidated__Manifest_v1'}
    return json.dumps(d).encode('utf-8')


def _make_config() -> bytes:
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.enums.Enum__Lets__Workflow__Type import Enum__Lets__Workflow__Type
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config    import Schema__Lets__Config
    cfg = Schema__Lets__Config(
        workflow_type          = Enum__Lets__Workflow__Type.CONSOLIDATE ,
        input_type             = 's3'                                    ,
        input_bucket           = BUCKET                                  ,
        input_prefix           = 'cloudfront-realtime/'                  ,
        input_format           = 'cf-realtime-tsv-gz'                   ,
        output_type            = 'ndjson-gz'                             ,
        output_schema          = 'Schema__CF__Event__Record'             ,
        output_schema_version  = 'v1'                                    ,
        output_compression     = 'gzip'                                  ,
        parser                 = 'CF__Realtime__Log__Parser'             ,
        parser_version         = _PARSER_VERSION                         ,
        bot_classifier         = 'Bot__Classifier'                       ,
        bot_classifier_version = '1.0.0'                                 ,
        consolidator           = 'Consolidate__Loader'                   ,
        consolidator_version   = '0.1.100'                               ,
        created_at             = '2026-04-25T09:00:00Z'                  ,
        created_by             = 'test'                                  ,
    )
    return Lets__Config__Writer().to_bytes(cfg)


def _make_ndjson_gz(n: int = 3) -> bytes:
    return NDJSON__Writer().records_to_bytes(_make_event_records(n))


def build_loader(fixture_objects: dict) -> Events__Loader:
    s3_fetcher = S3__Object__Fetcher__In_Memory(fixture_objects=fixture_objects, get_calls=[])
    http       = Inventory__HTTP__Client__In_Memory(
        bulk_calls=[], bulk_calls_opts=[], fixture_response=(),
        delete_pattern_calls=[], fixture_delete_pattern_response=(),
        count_pattern_calls=[], fixture_count_response=(),
        aggregate_calls=[], fixture_run_buckets=[],
        terms_update_calls=[], refresh_calls=[], template_calls=[])
    kb = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                    dashboard_calls=[], harden_calls=[],
                                                    delete_object_calls=[], import_calls=[],
                                                    find_calls=[], fixture_find_objects={})
    return Events__Loader(
        s3_lister         = S3__Inventory__Lister__In_Memory(fixture_pages=[], paginate_calls=[]),
        s3_fetcher        = s3_fetcher                                         ,
        parser            = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()),
        http_client       = http                                                ,
        kibana_client     = kb                                                  ,
        manifest_reader   = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[], list_calls=[], fixture_response=()),
        manifest_updater  = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[]),
        run_id_gen        = Deterministic__Run__Id__Generator()                 ,
        runs_tracker      = Pipeline__Runs__Tracker__In_Memory(record_calls=[], fixture_response=()),
        ndjson_reader     = NDJSON__Reader()                                    ,
        config_reader     = Lets__Config__Reader()                              ,
    )


def _full_fixture() -> dict:
    return {CONFIG_KEY  : _make_config()        ,
             MANIFEST_KEY: _make_manifest()      ,
             EVENTS_KEY  : _make_ndjson_gz(3)    }


def make_request(**kwargs) -> Schema__Events__Load__Request:
    defaults = dict(from_consolidated=True, date_iso=DATE_ISO, compat_region=COMPAT,
                    bucket=BUCKET, stack_name='test-stack')
    defaults.update(kwargs)
    return Schema__Events__Load__Request(**defaults)


class test_Events__Loader__from_consolidated__happy_path(TestCase):

    def test_returns_typed_response(self):
        loader = build_loader(_full_fixture())
        resp   = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert isinstance(resp, Schema__Events__Load__Response)

    def test_queue_mode_is_from_consolidated(self):
        loader = build_loader(_full_fixture())
        resp   = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert resp.queue_mode == 'from-consolidated'

    def test_events_indexed_from_ndjson(self):
        loader = build_loader(_full_fixture())
        resp   = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert resp.events_indexed == 3
        assert resp.error_message  == ''

    def test_single_bulk_post_call(self):
        loader = build_loader(_full_fixture())
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        http = loader.http_client
        assert len(http.bulk_calls) == 1
        _, index, doc_count, _ = http.bulk_calls[0]
        assert 'sg-cf-events-2026-04-25' in index
        assert doc_count == 3

    def test_bulk_post_uses_refresh_false(self):
        loader = build_loader(_full_fixture())
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        http = loader.http_client
        refresh, routing, _, _ = http.bulk_calls_opts[0]
        assert refresh  is False
        assert routing  == DATE_ISO

    def test_inventory_updated_via_terms_query_on_consolidation_run_id(self):
        loader = build_loader(_full_fixture())
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        http = loader.http_client
        assert len(http.terms_update_calls) == 1
        _, pattern, field, n_values, _ = http.terms_update_calls[0]
        assert pattern   == 'sg-cf-inventory-*'
        assert field     == 'consolidation_run_id'
        assert n_values  == 1                                                       # [CONSOL_RUN]

    def test_pipeline_run_journaled(self):
        loader = build_loader(_full_fixture())
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        tracker = loader.runs_tracker
        assert len(tracker.record_calls) == 1
        _, run_doc = tracker.record_calls[0]
        assert run_doc['queue_mode'] == 'from-consolidated'


class test_Events__Loader__from_consolidated__errors(TestCase):

    def test_missing_date_iso_returns_error(self):
        loader = build_loader(_full_fixture())
        resp   = loader.load(request=make_request(date_iso=''),
                              base_url='https://es', username='u', password='p')
        assert resp.error_message != ''

    def test_missing_config_returns_error(self):
        fixture = {MANIFEST_KEY: _make_manifest(), EVENTS_KEY: _make_ndjson_gz()}  # No config
        loader  = build_loader(fixture)
        resp    = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert resp.error_message != ''
        assert 'lets-config.json missing' in resp.error_message or 'compat_region' in resp.error_message

    def test_missing_manifest_returns_error(self):
        fixture = {CONFIG_KEY: _make_config(), EVENTS_KEY: _make_ndjson_gz()}      # No manifest
        loader  = build_loader(fixture)
        resp    = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert resp.error_message != ''
        assert 'manifest' in resp.error_message or 'date' in resp.error_message

    def test_missing_events_gz_returns_error(self):
        fixture = {CONFIG_KEY: _make_config(), MANIFEST_KEY: _make_manifest()}     # No events.ndjson.gz
        loader  = build_loader(fixture)
        resp    = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert resp.error_message != ''
