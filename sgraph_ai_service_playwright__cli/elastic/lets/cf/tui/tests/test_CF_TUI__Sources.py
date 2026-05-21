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

KEY_A = 'cloudfront-realtime/2026/04/21/08/stream-1-2026-04-21-08-00-01-a1b2c3.gz'
KEY_B = 'cloudfront-realtime/2026/04/21/08/stream-1-2026-04-21-08-00-02-a1b2c3.gz'
KEY_TO_LINE = {KEY_A: LINE_ENHANCECP,
               KEY_B: LINE_ROBOTS}


PREFIXES_SEEN = []                                                                   # records the prefix the source asked the lister for


class Lister__In_Memory(S3__Inventory__Lister):
    def paginate(self, bucket='', prefix='', max_keys=0, region=''):
        PREFIXES_SEEN.append(prefix)
        objects = [{'Key': 'cloudfront-realtime/2026/04/21/08/stream-1-2026-04-21-08-00-01-a1b2c3.gz', 'LastModified': '2026-04-21T08:00:01', 'Size': 480},
                   {'Key': 'cloudfront-realtime/2026/04/21/08/stream-1-2026-04-21-08-00-02-a1b2c3.gz', 'LastModified': '2026-04-21T08:00:02', 'Size': 510}]
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

    def test_scoped_prefix_from_date_and_hour(self):
        source = CF_TUI__S3_Source(date_iso='2026-04-21', hour='08', lister=Lister__In_Memory(), fetcher=Fetcher__In_Memory()).setup()
        assert source.scoped_prefix() == 'cloudfront-realtime/2026/04/21/08/'
        PREFIXES_SEEN.clear()
        source.list_files()                                                          # the lister should be asked for the scoped prefix
        assert PREFIXES_SEEN == ['cloudfront-realtime/2026/04/21/08/']

    def test_list_files_returns_metadata_rows(self):
        source = CF_TUI__S3_Source(lister=Lister__In_Memory(), fetcher=Fetcher__In_Memory()).setup()
        rows   = source.list_files()
        assert len(rows) == 2
        assert rows[0].size_bytes   in (480, 510)
        assert rows[0].delivery_iso != ''                                            # Firehose timestamp parsed from the filename

    def test_read_file_parses_one_object(self):
        source = CF_TUI__S3_Source(lister=Lister__In_Memory(), fetcher=Fetcher__In_Memory()).setup()
        view   = source.read_file(KEY_A)
        assert view.total_events == 1
        assert view.events[0].uri    == '/enhancecp'
        assert view.events[0].status == 302
        assert view.events[0].is_bot is True
        assert 'enhancecp' in view.raw_text


def test_scoped_prefix_uses_args():
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__S3_Source import CF_TUI__S3_Source
    s = CF_TUI__S3_Source()
    assert s.scoped_prefix('2026-05-21')        == 'cloudfront-realtime/2026/05/21/'
    assert s.scoped_prefix('2026/05/21', '00')  == 'cloudfront-realtime/2026/05/21/00/'
    assert s.scoped_prefix()                    == 'cloudfront-realtime/'


class test_CF_TUI__In_Memory_Source__files(TestCase):

    def source(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Fixture_File import Schema__CF_TUI__Fixture_File
        src = CF_TUI__In_Memory_Source().setup()
        src.files.append(Schema__CF_TUI__Fixture_File(key='hour-08/file-a.gz', tsv_text=LINE_ENHANCECP))
        src.files.append(Schema__CF_TUI__Fixture_File(key='hour-08/file-b.gz', tsv_text=LINE_ROBOTS))
        return src

    def test_list_files_lists_each_blob(self):
        rows = self.source().list_files()
        assert {r.key for r in rows} == {'hour-08/file-a.gz', 'hour-08/file-b.gz'}
        assert all(r.size_bytes > 0 for r in rows)

    def test_read_file_parses_named_blob(self):
        view = self.source().read_file('hour-08/file-b.gz')
        assert view.total_events  == 1
        assert view.events[0].uri == '/robots.txt'

    def test_traffic_aggregates_across_files(self):
        snap = self.source().traffic_snapshot()
        assert snap.total_events  == 2
        assert snap.files_sampled == 2

    def test_default_single_fixture_file(self):                                      # tsv_text shorthand → one "fixtures.tsv"
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures import FIXTURE_TSV
        rows = CF_TUI__In_Memory_Source(tsv_text=FIXTURE_TSV).setup().list_files()
        assert len(rows) == 1
        assert rows[0].key == 'fixtures.tsv'
