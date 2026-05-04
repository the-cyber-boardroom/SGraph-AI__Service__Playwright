# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Consolidate__Loader
# End-to-end orchestrator tests using every collaborator's *__In_Memory variant.
# No mocks.  Pins:
#   - happy path: accumulates records from 2 source files, writes ndjson.gz + manifest
#   - dry_run: returns queue count, skips all I/O
#   - fetch error: files_skipped increments, loop continues with next file
#   - lets-config.json written on first use
#   - lets-config.json validated on subsequent use (compat mismatch → error)
#   - inventory docs stamped via single update_by_query_terms (E-6)
#   - manifest doc indexed into sg-cf-consolidated-{date}
#   - pipeline run journaled via Pipeline__Runs__Tracker
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidate__Load__Request  import Schema__Consolidate__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidate__Load__Response import Schema__Consolidate__Load__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config               import Schema__Lets__Config
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Consolidate__Loader                 import Consolidate__Loader, s3_key_for_config, s3_key_for_events, s3_key_for_manifest
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Reader                import Lets__Config__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Lets__Config__Writer                import Lets__Config__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Manifest__Builder                   import Manifest__Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Writer                      import NDJSON__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Reader                      import NDJSON__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier                          import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser               import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.runs.enums.Enum__Pipeline__Verb                           import Enum__Pipeline__Verb

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.S3__Object__Writer__In_Memory  import S3__Object__Writer__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher__In_Memory       import S3__Object__Fetcher__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister__In_Memory  import S3__Inventory__Lister__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.test_Run__Id__Generator           import Deterministic__Run__Id__Generator
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker__In_Memory         import Pipeline__Runs__Tracker__In_Memory


# ─── minimal CF-realtime log line fixture ─────────────────────────────────────
LINE_A = ('1777075217.167\t0.001\t200\t246\tGET\thttps\tsgraph.ai\t/page\t'
          'HIO52-P4\tREQID001==\t0.001\tHTTP/2.0\tMozilla/5.0\t-\t'
          'Hit\tTLSv1.3\tTLS_AES_128_GCM_SHA256\t-\t0\t-\t-\tUS\tgzip\t-\t-\t-')
LINE_B = ('1777075217.200\t0.002\t404\t100\tGET\thttps\tsgraph.ai\t/missing\t'
          'HIO52-P4\tREQID002==\t0.002\tHTTP/2.0\tMozilla/5.0\t-\t'
          'Error\tTLSv1.3\tTLS_AES_128_GCM_SHA256\t-\t0\t-\t-\tUS\tgzip\t-\t-\t-')

GZ_FILE_1 = gzip.compress((LINE_A + '\n').encode('utf-8'))                          # 1 event
GZ_FILE_2 = gzip.compress((LINE_B + '\n').encode('utf-8'))                          # 1 event

DATE_ISO    = '2026-04-25'
BUCKET      = '745506449035--sgraph-send-cf-logs--eu-west-2'
ETAG_1      = 'aaaa0001bbbb0002cccc0003dddd0004'
ETAG_2      = 'eeee0001ffff0002aaaa0003bbbb0004'
KEY_1       = f'cloudfront-realtime/2026/04/25/file1.gz'
KEY_2       = f'cloudfront-realtime/2026/04/25/file2.gz'
COMPAT      = 'raw-cf-to-consolidated'
CONFIG_KEY  = s3_key_for_config(COMPAT)
EVENTS_KEY  = s3_key_for_events(COMPAT, DATE_ISO)
MANIFEST_KEY = s3_key_for_manifest(COMPAT, DATE_ISO)


def make_http() -> Inventory__HTTP__Client__In_Memory:
    return Inventory__HTTP__Client__In_Memory(
        bulk_calls=[], bulk_calls_opts=[], fixture_response=(),
        delete_pattern_calls=[], fixture_delete_pattern_response=(),
        count_pattern_calls=[], fixture_count_response=(),
        aggregate_calls=[], fixture_run_buckets=[],
        terms_update_calls=[], refresh_calls=[], template_calls=[])


def build_loader(fixture_objects   : dict = None,
                  s3_pages          : list = None,
                  http              : Inventory__HTTP__Client__In_Memory = None,
                  preloaded_s3      : dict = None,                               # bytes already in s3_writer.written before the run
                  ) -> tuple:                                                    # (Consolidate__Loader, s3_writer, http)
    actual_fetcher_objects = fixture_objects if fixture_objects is not None else {
        KEY_1: GZ_FILE_1, KEY_2: GZ_FILE_2}
    s3_fetcher = S3__Object__Fetcher__In_Memory(fixture_objects=actual_fetcher_objects, get_calls=[])
    s3_writer  = S3__Object__Writer__In_Memory(put_calls=[], written=preloaded_s3 or {})
    s3_lister  = S3__Inventory__Lister__In_Memory(fixture_pages=s3_pages or [], paginate_calls=[])
    if http is None:
        http = make_http()
    loader = Consolidate__Loader(
        s3_fetcher       = s3_fetcher                                   ,
        s3_writer        = s3_writer                                    ,
        s3_lister        = s3_lister                                    ,
        parser           = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()),
        http_client      = http                                         ,
        ndjson_writer    = NDJSON__Writer()                             ,
        manifest_builder = Manifest__Builder()                          ,
        config_reader    = Lets__Config__Reader()                       ,
        config_writer    = Lets__Config__Writer()                       ,
        run_id_gen       = Deterministic__Run__Id__Generator()          ,
        runs_tracker     = Pipeline__Runs__Tracker__In_Memory(record_calls=[], fixture_response=()),
    )
    return loader, s3_writer, http


def make_request(**kwargs) -> Schema__Consolidate__Load__Request:
    defaults = dict(bucket=BUCKET, date_iso=DATE_ISO, compat_region=COMPAT,
                    from_inventory=False, max_files=0, stack_name='test-stack')
    defaults.update(kwargs)
    return Schema__Consolidate__Load__Request(**defaults)


class test_Consolidate__Loader__happy_path(TestCase):

    def test_returns_typed_response(self):
        loader, _, _ = build_loader()
        resp = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert isinstance(resp, Schema__Consolidate__Load__Response)

    def test_two_source_files_two_events(self):
        loader, _, _ = build_loader(s3_pages=[[
            {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': len(GZ_FILE_1)},
            {'Key': KEY_2, 'ETag': f'"{ETAG_2}"', 'Size': len(GZ_FILE_2)},
        ]])
        resp = loader.load(request=make_request(from_inventory=False, max_files=2),
                            base_url='https://es', username='u', password='p')
        assert resp.files_queued        == 2
        assert resp.files_processed     == 2
        assert resp.files_skipped       == 0
        assert resp.events_consolidated == 2
        assert resp.error_message       == ''

    def test_events_ndjson_gz_written_to_s3(self):
        loader, s3_writer, _ = build_loader()
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        written_keys = [key for (_, key, _, _) in s3_writer.put_calls]
        assert EVENTS_KEY in written_keys

    def test_manifest_json_written_to_s3(self):
        loader, s3_writer, _ = build_loader()
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        written_keys = [key for (_, key, _, _) in s3_writer.put_calls]
        assert MANIFEST_KEY in written_keys

    def test_lets_config_written_on_first_use(self):
        loader, s3_writer, _ = build_loader()                                       # No pre-existing config in fetcher
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        written_keys = [key for (_, key, _, _) in s3_writer.put_calls]
        assert CONFIG_KEY in written_keys

    def test_events_ndjson_gz_is_valid_gzip_ndjson(self):
        loader, s3_writer, _ = build_loader(s3_pages=[[
            {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': len(GZ_FILE_1)}]])
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        gz_bytes = s3_writer.written.get((BUCKET, EVENTS_KEY))
        assert gz_bytes is not None
        reader  = NDJSON__Reader()
        records = reader.bytes_to_records(gz_bytes)
        assert len(records) > 0

    def test_manifest_json_is_valid_json(self):
        loader, s3_writer, _ = build_loader()
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        manifest_bytes = s3_writer.written.get((BUCKET, MANIFEST_KEY))
        assert manifest_bytes is not None
        d = json.loads(manifest_bytes.decode('utf-8'))
        assert d['date_iso'] == DATE_ISO

    def test_bytes_written_matches_ndjson_gz_size(self):
        loader, s3_writer, _ = build_loader()
        resp = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        gz_bytes = s3_writer.written.get((BUCKET, EVENTS_KEY))
        assert resp.bytes_written == len(gz_bytes)

    def test_s3_output_key_in_response(self):
        loader, _, _ = build_loader()
        resp = loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert str(resp.s3_output_key) == EVENTS_KEY


class test_Consolidate__Loader__dry_run(TestCase):

    def test_dry_run_returns_queue_count_no_writes(self):
        loader, s3_writer, http = build_loader(s3_pages=[[
            {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': 386},
            {'Key': KEY_2, 'ETag': f'"{ETAG_2}"', 'Size': 386},
        ]])
        resp = loader.load(request=make_request(from_inventory=False, max_files=2, dry_run=True),
                            base_url='https://es', username='u', password='p')
        assert resp.dry_run         is True
        assert resp.files_queued    == 2
        assert resp.files_processed == 0
        assert len(s3_writer.put_calls) == 0
        assert len(http.bulk_calls)     == 0


class test_Consolidate__Loader__error_handling(TestCase):

    def test_fetch_error_counts_as_skipped(self):
        loader, _, _ = build_loader(fixture_objects={KEY_1: GZ_FILE_1},             # KEY_2 missing → KeyError
                                     s3_pages=[[
                                         {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': 100},
                                         {'Key': KEY_2, 'ETag': f'"{ETAG_2}"', 'Size': 100},
                                     ]])
        resp = loader.load(request=make_request(from_inventory=False, max_files=2),
                            base_url='https://es', username='u', password='p')
        assert resp.files_queued    == 2
        assert resp.files_processed == 1
        assert resp.files_skipped   == 1
        assert resp.error_message   != ''

    def test_fetch_error_loop_continues(self):
        loader, s3_writer, _ = build_loader(fixture_objects={KEY_1: GZ_FILE_1},     # KEY_2 missing
                                              s3_pages=[[
                                                  {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': 100},
                                                  {'Key': KEY_2, 'ETag': f'"{ETAG_2}"', 'Size': 100},
                                              ]])
        loader.load(request=make_request(from_inventory=False, max_files=2),
                     base_url='https://es', username='u', password='p')
        assert EVENTS_KEY in [k for (_, k, _, _) in s3_writer.put_calls]            # ndjson.gz still written from KEY_1


class test_Consolidate__Loader__elastic(TestCase):

    def test_manifest_indexed_into_consolidated_index(self):
        loader, _, http = build_loader()
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        # bulk_calls contains (base_url, index, doc_count, id_field) 4-tuples
        indices = [idx for (_, idx, _, _) in http.bulk_calls]
        assert any('sg-cf-consolidated' in idx for idx in indices)

    def test_inventory_docs_stamped_via_terms_update(self):
        loader, _, http = build_loader(s3_pages=[[
            {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': len(GZ_FILE_1)}]])
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        # terms_update_calls: [(base_url, index_pattern, field, len(values), script_source)]
        assert len(http.terms_update_calls) == 1
        _, pattern, field, _, _ = http.terms_update_calls[0]
        assert pattern == 'sg-cf-inventory-*'
        assert field   == 'etag'

    def test_pipeline_run_journaled_with_consolidate_verb(self):
        loader, _, http = build_loader(s3_pages=[[
            {'Key': KEY_1, 'ETag': f'"{ETAG_1}"', 'Size': len(GZ_FILE_1)}]])
        runs_tracker = loader.runs_tracker
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert len(runs_tracker.record_calls) == 1
        _, run_doc = runs_tracker.record_calls[0]
        assert run_doc['verb'] == str(Enum__Pipeline__Verb.CONSOLIDATE_LOAD)


class test_Consolidate__Loader__config(TestCase):

    def test_compat_config_accepted_on_rerun(self):
        loader, s3_writer, _ = build_loader()
        # First run writes config
        loader.load(request=make_request(), base_url='https://es', username='u', password='p')
        config_bytes = s3_writer.written.get((BUCKET, CONFIG_KEY))
        assert config_bytes is not None
        # Second run: pre-seed the config in fetcher so it's "already there"
        loader2, _, _ = build_loader(fixture_objects={
            KEY_1: GZ_FILE_1, KEY_2: GZ_FILE_2, CONFIG_KEY: config_bytes})
        resp2 = loader2.load(request=make_request(), base_url='https://es', username='u', password='p')
        assert resp2.error_message == ''
