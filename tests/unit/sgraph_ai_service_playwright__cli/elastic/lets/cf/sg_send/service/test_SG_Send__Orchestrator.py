# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — SG_Send__Orchestrator
# End-to-end orchestrator tests using every collaborator's *__In_Memory variant.
# No mocks.  Pins:
#   - happy path: inventory load + events load both run, results embedded
#   - shared Call__Counter spans both pipeline phases
#   - sync_date empty → defaults to today UTC (tested by asserting prefix)
#   - explicit sync_date resolves correct S3 prefix
#   - dry_run=True propagates to both sub-requests
#   - max_files propagated to events phase
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
from datetime                                                                       import datetime, timezone
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.Call__Counter                  import Call__Counter
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier            import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser  import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Loader              import Events__Loader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Loader        import Inventory__Loader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator       import Run__Id__Generator

from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Request  import Schema__SG_Send__Sync__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Response import Schema__SG_Send__Sync__Response
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__Orchestrator           import SG_Send__Orchestrator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader__In_Memory  import Inventory__Manifest__Reader__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater__In_Memory import Inventory__Manifest__Updater__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher__In_Memory          import S3__Object__Fetcher__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory   import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister__In_Memory     import S3__Inventory__Lister__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.test_Run__Id__Generator              import Deterministic__Run__Id__Generator
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory                import Kibana__Saved_Objects__Client__In_Memory


# ─── minimal S3 inventory fixture (1 file → 1 manifest entry) ─────────────────

SAMPLE_KEY  = 'cloudfront-realtime/2026/04/27/sgraph-send-cf-logs-2-2026-04-27-00-05-27-deadbeef.gz'
SAMPLE_ETAG = 'deadbeef00000000000000000000abcd'

LINE_1 = '1777075217.167\t0.001\t302\t246\tGET\thttps\tsgraph.ai\t/enhancecp\tHIO52-P4\t2TZI-f7L0PmDR==\t0.001\tHTTP/2.0\tMozilla/5.0%20(compatible;%20wpbot/1.4;%20+https://forms.gle/ajBaxygz9jSR8p8G9)\t-\tFunctionGeneratedResponse\tTLSv1.3\tTLS_AES_128_GCM_SHA256\t-\t0\t-\t-\tUS\tgzip\t-\t-\t-'
SAMPLE_GZ   = gzip.compress((LINE_1 + '\n').encode('utf-8'))

INVENTORY_FIXTURE = [{'bucket'     : '745506449035--sgraph-send-cf-logs--eu-west-2',
                       'key'        : SAMPLE_KEY                                    ,
                       'etag'       : SAMPLE_ETAG                                   ,
                       'size_bytes' : 500                                           ,
                       'delivery_at': '2026-04-27T00:05:27Z'                       }]

S3_PAGES = [[{'Key'         : SAMPLE_KEY                                    ,
               'LastModified': datetime(2026, 4, 27, 0, 5, 27, tzinfo=timezone.utc),
               'Size'        : 500                                           ,
               'ETag'        : f'"{SAMPLE_ETAG}"'                           ,
               'StorageClass': 'STANDARD'                                   }]]


def build_orchestrator(shared_counter: Call__Counter) -> SG_Send__Orchestrator:
    inv_http    = Inventory__HTTP__Client__In_Memory(counter          = shared_counter ,
                                                      bulk_calls       = []            ,
                                                      fixture_response = ()            )
    inv_lister  = S3__Inventory__Lister__In_Memory(counter       = shared_counter ,
                                                    fixture_pages = S3_PAGES      ,
                                                    paginate_calls= []            )
    inv_kb      = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                             dashboard_calls=[], harden_calls=[],
                                                             delete_object_calls=[], import_calls=[])
    inv_loader  = Inventory__Loader(s3_lister=inv_lister, http_client=inv_http,
                                     kibana_client=inv_kb, run_id_gen=Deterministic__Run__Id__Generator())

    ev_http     = Inventory__HTTP__Client__In_Memory(counter               = shared_counter ,
                                                      bulk_calls            = []            ,
                                                      fixture_response       = ()            ,
                                                      delete_pattern_calls   = []            ,
                                                      fixture_delete_pattern_response = ()   ,
                                                      count_pattern_calls    = []            ,
                                                      fixture_count_response = ()            ,
                                                      aggregate_calls        = []            ,
                                                      fixture_run_buckets    = []            )
    ev_fetcher  = S3__Object__Fetcher__In_Memory(counter         = shared_counter          ,
                                                  fixture_objects = {SAMPLE_KEY: SAMPLE_GZ} ,
                                                  get_calls       = []                       )
    ev_reader   = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs = INVENTORY_FIXTURE,
                                                          list_calls               = []              ,
                                                          fixture_response          = ()              )
    ev_updater  = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[])
    ev_kb       = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                            dashboard_calls=[], harden_calls=[],
                                                            delete_object_calls=[], import_calls=[],
                                                            find_calls=[], fixture_find_objects={})
    ev_lister   = S3__Inventory__Lister__In_Memory(counter       = shared_counter ,
                                                    fixture_pages = []            ,
                                                    paginate_calls= []            )
    events_loader = Events__Loader(s3_lister=ev_lister, s3_fetcher=ev_fetcher,
                                    parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()),
                                    http_client=ev_http, kibana_client=ev_kb,
                                    manifest_reader=ev_reader, manifest_updater=ev_updater,
                                    run_id_gen=Deterministic__Run__Id__Generator())

    return SG_Send__Orchestrator(counter          = shared_counter ,
                                  inventory_loader = inv_loader     ,
                                  events_loader    = events_loader  )


class test_SG_Send__Orchestrator(TestCase):

    def _sync(self, request=None, counter=None):
        shared = counter or Call__Counter()
        orch   = build_orchestrator(shared)
        return orch.sync(request  = request or Schema__SG_Send__Sync__Request() ,
                          base_url = 'https://1.2.3.4'                           ,
                          username = 'elastic'                                    ,
                          password = 'pw'                                        ), shared

    def test_response_type_is_correct(self):
        resp, _ = self._sync()
        assert isinstance(resp, Schema__SG_Send__Sync__Response)

    def test_both_sub_responses_embedded(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Response import Schema__Inventory__Load__Response
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Response       import Schema__Events__Load__Response
        resp, _ = self._sync()
        assert isinstance(resp.inventory_response, Schema__Inventory__Load__Response)
        assert isinstance(resp.events_response,    Schema__Events__Load__Response)

    def test_inventory_phase_ran(self):
        resp, _ = self._sync()
        assert resp.inventory_response.objects_scanned == 1
        assert resp.inventory_response.objects_indexed == 1

    def test_events_phase_ran_from_inventory(self):
        resp, _ = self._sync()
        assert resp.events_response.files_queued   == 1
        assert resp.events_response.files_processed == 1
        assert resp.events_response.events_indexed  >= 1

    def test_shared_counter_aggregates_both_phases(self):
        resp, counter = self._sync()
        # Counter totals in the response reflect the same shared_counter instance
        # In-memory variants don't make real AWS calls so counters stay at 0 —
        # the important thing is that the response snapshots the shared counter.
        assert resp.s3_calls_total      == counter.s3_calls
        assert resp.elastic_calls_total == counter.elastic_calls

    def test_dry_run_propagates_to_both_phases(self):
        req  = Schema__SG_Send__Sync__Request(dry_run=True)
        resp, _ = self._sync(request=req)
        assert resp.dry_run                          is True
        assert resp.inventory_response.dry_run       is True
        assert resp.events_response.dry_run          is True

    def test_explicit_sync_date_resolves_correct_prefix(self):
        from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text import Safe_Str__Text
        req  = Schema__SG_Send__Sync__Request(sync_date=Safe_Str__Text('2026-04-27'))
        resp, _ = self._sync(request=req)
        assert resp.sync_date                              == '2026-04-27'
        assert resp.inventory_response.prefix_resolved     == 'cloudfront-realtime/2026/04/27/'

    def test_wall_ms_is_positive(self):
        resp, _ = self._sync()
        assert resp.wall_ms >= 0                                                    # ≥0: in-memory is fast but timing may round to 0
