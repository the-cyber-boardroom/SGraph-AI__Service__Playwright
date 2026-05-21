# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf local: CF__Local__Store + CF__Logs__Sync
# Drives sync with fake S3 boundaries (subclass S3__Inventory__Lister / .Fetcher and
# override their seams) and a tmp-dir store — no AWS, no mocks. Covers the plan diff,
# the download-missing path (immutable skip), and the local stats rollup.
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
from pathlib  import Path
from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher       import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister  import S3__Inventory__Lister
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store           import CF__Local__Store
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Logs__Sync             import CF__Logs__Sync
from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log                               import Debug__Event_Log

PREFIX = 'cloudfront-realtime/'
KEYS   = [f'{PREFIX}2026/05/21/08/file-a.gz',
          f'{PREFIX}2026/05/21/08/file-b.gz',
          f'{PREFIX}2026/05/21/09/file-c.gz']


class FakeLister(S3__Inventory__Lister):
    def paginate(self, bucket, prefix='', max_keys=0, region=''):
        objs = [{'Key': k, 'Size': 100 + i, 'LastModified': '2026-05-21'} for i, k in enumerate(KEYS) if k.startswith(prefix)]
        return objs, 1


class FakeFetcher(S3__Object__Fetcher):
    def get_object_bytes(self, bucket, key, region=''):
        return b'X' * (100 + KEYS.index(key))


def sync(tmp):
    return CF__Logs__Sync(lister  = FakeLister(),
                          fetcher = FakeFetcher(),
                          store   = CF__Local__Store(root=tmp, src_prefix=PREFIX),
                          debug   = Debug__Event_Log())


class test_CF__Logs__Sync(TestCase):

    def test_plan_all_missing_then_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc  = sync(tmp)
            plan = svc.plan('2026-05-21')
            assert plan.remote_count  == 3
            assert plan.local_count   == 0
            assert plan.missing_count == 3
            assert all(f.present_local is False for f in plan.files)

            result = svc.download_missing(plan)
            assert result.downloaded == 3
            assert result.skipped    == 0
            assert result.done       is True
            # files now on disk under the partition layout
            assert (Path(tmp) / 'raw-cf-logs' / '2026/05/21/08/file-a.gz').is_file()

            # re-plan: immutable → all present, nothing to fetch
            plan2 = svc.plan('2026-05-21')
            assert plan2.missing_count == 0
            result2 = svc.download_missing(plan2)
            assert result2.downloaded == 0
            assert result2.skipped    == 3

    def test_hour_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = sync(tmp).plan('2026-05-21', '09')
            assert plan.remote_count == 1
            assert plan.files[0].key.endswith('file-c.gz')

    def test_debug_log_records_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc  = sync(tmp)
            svc.download_missing(svc.plan('2026-05-21'))
            cats = {e.category for e in svc.debug.events}
            assert 's3.list'  in cats
            assert 's3.get'   in cats
            assert 'fs.write' in cats


class test_CF__Local__Store__stats(TestCase):

    def test_stats_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = sync(tmp)
            svc.download_missing(svc.plan('2026-05-21'))
            stats = svc.store.stats()
            assert stats.exists      is True
            assert stats.total_files == 3
            assert stats.day_count   == 1
            assert stats.hour_count  == 2                                            # hours 08 and 09
            assert stats.first_day   == '2026/05/21'
            assert stats.days[0].files == 3

    def test_stats_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats = CF__Local__Store(root=tmp).stats()
            assert stats.exists      is False
            assert stats.total_files == 0
