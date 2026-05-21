# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: data sources
# In_Memory source over the golden fixtures, and the S3 source driven by in-memory
# subclasses of the LETS S3 boundaries (override paginate / get_object_bytes to
# return gzipped fixture bytes) — the no-mock pattern, no AWS round-trips. Both
# render the same normalised snapshot, proving the seam.
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher     import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV, LINE_ENHANCECP, LINE_ROBOTS
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source  import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__In_Memory_Source import CF_TUI__In_Memory_Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__S3_Source    import CF_TUI__S3_Source


class test_CF_TUI__In_Memory_Source(TestCase):

    def test_snapshot_from_fixtures(self):
        source   = CF_TUI__In_Memory_Source(tsv_text=FIXTURE_TSV).setup()
        snapshot = source.traffic_snapshot()
        assert source.source()        == Enum__CF_TUI__Source.IN_MEMORY
        assert 'fixtures'             in source.label()
        assert snapshot.total_events  == 2
        assert snapshot.files_sampled == 1
        assert snapshot.bot_events    == 2

    def test_empty_text_zero_files(self):
        snapshot = CF_TUI__In_Memory_Source(tsv_text='').setup().traffic_snapshot()
        assert snapshot.total_events  == 0
        assert snapshot.files_sampled == 0


# ─── in-memory S3 boundaries (no AWS, no mocks — subclass + override) ─────────

KEY_TO_LINE = {'cloudfront-realtime/2026/04/21/08/a.gz': LINE_ENHANCECP,
               'cloudfront-realtime/2026/04/21/08/b.gz': LINE_ROBOTS}


class Lister__In_Memory(S3__Inventory__Lister):
    def paginate(self, bucket='', prefix='', max_keys=0, region=''):
        objects = [{'Key': 'cloudfront-realtime/2026/04/21/08/a.gz', 'LastModified': '2026-04-21T08:00:01'},
                   {'Key': 'cloudfront-realtime/2026/04/21/08/b.gz', 'LastModified': '2026-04-21T08:00:02'}]
        return objects, 1


class Fetcher__In_Memory(S3__Object__Fetcher):
    def get_object_bytes(self, bucket='', key='', region=''):
        return gzip.compress(KEY_TO_LINE[key].encode('utf-8'))


class test_CF_TUI__S3_Source(TestCase):

    def test_snapshot_reads_lists_fetches_parses(self):
        source   = CF_TUI__S3_Source(lister=Lister__In_Memory(), fetcher=Fetcher__In_Memory()).setup()
        snapshot = source.traffic_snapshot()
        assert source.source()        == Enum__CF_TUI__Source.S3
        assert snapshot.total_events  == 2                                            # both .gz objects parsed
        assert snapshot.files_sampled == 2
        assert snapshot.bot_events    == 2
        assert snapshot.source.value  == 's3'

    def test_label_is_bucket_prefix(self):
        source = CF_TUI__S3_Source(bucket='b', prefix='p/', lister=Lister__In_Memory(), fetcher=Fetcher__In_Memory()).setup()
        assert source.label() == 's3://b/p/'
