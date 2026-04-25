# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — S3__Inventory__Lister
# Drives the lister via its in-memory subclass so we can pin pagination,
# max_keys mid-page truncation, the empty-page tolerance, and the call-args
# capture. Also exercises normalise_etag.
# No boto3, no AWS, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import normalise_etag

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister__In_Memory import S3__Inventory__Lister__In_Memory


def s3_object(key: str, size: int = 386, etag: str = 'e71885f47b8c4d4fa930e1c6e7083682') -> dict:
    return {'Key'         : key                                              ,
            'LastModified': datetime(2026, 4, 25, 0, 5, 27, tzinfo=timezone.utc),
            'Size'        : size                                             ,
            'ETag'        : f'"{etag}"'                                      ,    # AWS returns ETag wrapped in quotes
            'StorageClass': 'STANDARD'                                       }


class test_S3__Inventory__Lister(TestCase):

    def test_starts_with_no_calls(self):
        lister = S3__Inventory__Lister__In_Memory(fixture_pages = [], paginate_calls = [])
        assert lister.paginate_calls == []

    def test_single_page_three_objects(self):
        page   = [s3_object(f'cf/2026/04/25/file-{i}.gz') for i in range(3)]
        lister = S3__Inventory__Lister__In_Memory(fixture_pages = [page], paginate_calls = [])
        objects, pages = lister.paginate(bucket='b', prefix='cf/2026/04/25/')
        assert pages           == 1
        assert len(objects)    == 3
        assert objects[0]['Key'] == 'cf/2026/04/25/file-0.gz'

    def test_multi_page_aggregates(self):
        pages_in = [[s3_object(f'k-{i}-{j}.gz') for j in range(2)] for i in range(3)]
        lister   = S3__Inventory__Lister__In_Memory(fixture_pages = pages_in, paginate_calls = [])
        objects, pages = lister.paginate(bucket='b')
        assert pages        == 3
        assert len(objects) == 6

    def test_max_keys_truncates_mid_page(self):                                     # Stop once we've collected max_keys, even partway through a page
        page    = [s3_object(f'k-{i}.gz') for i in range(10)]
        lister  = S3__Inventory__Lister__In_Memory(fixture_pages = [page], paginate_calls = [])
        objects, pages = lister.paginate(bucket='b', max_keys=4)
        assert pages        == 1
        assert len(objects) == 4

    def test_empty_pages_tolerated(self):                                           # Real S3 returns pages with no Contents when the prefix is empty
        lister = S3__Inventory__Lister__In_Memory(fixture_pages = [[], [], []], paginate_calls = [])
        objects, pages = lister.paginate(bucket='b', prefix='nonexistent/')
        assert pages        == 3                                                    # We still consumed the pages
        assert objects      == []

    def test_call_args_captured(self):                                              # Lets the loader's tests assert on (bucket, prefix, max_keys, region) downstream
        lister = S3__Inventory__Lister__In_Memory(fixture_pages = [], paginate_calls = [])
        lister.paginate(bucket='b', prefix='p', max_keys=42, region='eu-west-2')
        assert lister.paginate_calls == [('b', 'p', 42, 'eu-west-2')]


class test_normalise_etag(TestCase):

    def test_strips_surrounding_quotes(self):                                       # AWS returns ETag with quotes; the Safe_Str__S3__ETag regex doesn't accept them
        assert normalise_etag('"e71885f47b8c4d4fa930e1c6e7083682"') == 'e71885f47b8c4d4fa930e1c6e7083682'

    def test_lowercases(self):
        assert normalise_etag('"E71885F47B8C4D4FA930E1C6E7083682"') == 'e71885f47b8c4d4fa930e1c6e7083682'

    def test_handles_empty(self):
        assert normalise_etag('') == ''

    def test_already_normalised_passes_through(self):
        assert normalise_etag('e71885f47b8c4d4fa930e1c6e7083682') == 'e71885f47b8c4d4fa930e1c6e7083682'
