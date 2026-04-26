# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Loader
# End-to-end orchestrator tests using every collaborator's *__In_Memory variant
# — no mocks. Pins:
#   - happy path (list → records → ensure data view → bulk-post)
#   - dry-run skips the bulk-post and returns dry_run=True
#   - empty bucket returns zero counts cleanly
#   - default prefix resolves to "cloudfront-realtime/{today UTC}/"
#   - explicit prefix wins over the today default
#   - --all flag clears the prefix entirely
#   - run_id auto-generates when empty
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timezone
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Request import Schema__Inventory__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Loader import Inventory__Loader, default_prefix_for_today

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister__In_Memory  import S3__Inventory__Lister__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.test_Run__Id__Generator           import Deterministic__Run__Id__Generator
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory             import Kibana__Saved_Objects__Client__In_Memory


# ─── one Firehose-shaped page (3 objects spanning ~13 minutes) ────────────────
def sample_pages() -> list:
    return [[{'Key'         : f'cloudfront-realtime/2026/04/25/sgraph-send-cf-logs-to-s3-2-2026-04-25-00-{minute:02d}-{minute:02d}-deadbeef-{i:04x}.gz',
              'LastModified': datetime(2026, 4, 25, 0, minute + 1, 27, tzinfo=timezone.utc),
              'Size'        : 386 + i * 100,
              'ETag'        : f'"{(i + 1):032x}"',                                  # Quoted, AWS-style
              'StorageClass': 'STANDARD'                                          }
              for i, minute in enumerate([0, 13, 14])]]


def build_loader(s3_pages: list = None,
                  http_response: tuple = ()) -> Inventory__Loader:
    s3 = S3__Inventory__Lister__In_Memory(fixture_pages = s3_pages or sample_pages(),
                                           paginate_calls = []                       )
    http = Inventory__HTTP__Client__In_Memory(bulk_calls       = [] ,
                                               fixture_response = http_response)
    kb   = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                     dashboard_calls=[], harden_calls=[],
                                                     delete_object_calls=[])
    gen  = Deterministic__Run__Id__Generator()
    return Inventory__Loader(s3_lister=s3, http_client=http, kibana_client=kb, run_id_gen=gen)


class test_Inventory__Loader(TestCase):

    def test_happy_path_returns_full_response(self):
        loader = build_loader()
        resp   = loader.load(request  = Schema__Inventory__Load__Request(prefix='cloudfront-realtime/2026/04/25/'),
                              base_url = 'https://1.2.3.4',
                              username = 'elastic',
                              password = 'pw')
        assert resp.run_id           == '20260425T103042Z-cf-realtime-load-a3f2'
        assert resp.bucket           == '745506449035--sgraph-send-cf-logs--eu-west-2'
        assert resp.prefix_resolved  == 'cloudfront-realtime/2026/04/25/'
        assert resp.pages_listed     == 1
        assert resp.objects_scanned  == 3
        assert resp.objects_indexed  == 3
        assert resp.bytes_total      == 386 + 486 + 586                              # Sum of Sizes from sample_pages
        assert resp.last_http_status == 200
        assert resp.error_message    == ''
        assert resp.dry_run          is False
        assert resp.kibana_url       == 'https://1.2.3.4/app/dashboards'

    def test_bulk_post_called_with_etag_id_and_delivery_dated_index(self):          # Index name is keyed on the data's delivery date, NOT today/loaded_at
        loader = build_loader()                                                     # All sample records share delivery_at = 2026-04-25
        loader.load(request  = Schema__Inventory__Load__Request(prefix='cloudfront-realtime/2026/04/25/'),
                     base_url = 'https://1.2.3.4', username='u', password='p')
        assert len(loader.http_client.bulk_calls) == 1                              # One bulk call (single day)
        base_url, index, count, id_field = loader.http_client.bulk_calls[0]
        assert id_field == 'etag'
        assert count    == 3
        assert index    == 'sg-cf-inventory-2026-04-25'                              # Delivery date, not loaded_at

    def test_data_view_uses_wildcard_pattern(self):                                 # Pattern must match "sg-cf-inventory-*" for daily indices to surface
        loader = build_loader()
        loader.load(request  = Schema__Inventory__Load__Request(prefix='cloudfront-realtime/2026/04/25/'),
                     base_url = 'https://1.2.3.4', username='u', password='p')
        assert loader.kibana_client.ensure_calls == [('https://1.2.3.4', 'sg-cf-inventory-*', 'delivery_at')]

    def test_multi_day_records_split_across_per_day_indices(self):                  # Records spanning multiple delivery dates produce one bulk-post per date
        from datetime import datetime, timezone
        pages = [[{'Key'         : f'cloudfront-realtime/2026/04/{day:02d}/sgraph-send-cf-logs-to-s3-2-2026-04-{day:02d}-12-00-00-deadbeef-{i:04x}.gz',
                   'LastModified': datetime(2026, 4, day, 12, 0, 30, tzinfo=timezone.utc),
                   'Size'        : 100,
                   'ETag'        : f'"{(day * 10 + i):032x}"',
                   'StorageClass': 'STANDARD'                                       }
                  for day in (24, 25, 26) for i in range(2)]]                         # 6 records: 2 per day for three delivery dates
        loader = build_loader(s3_pages=pages)
        loader.load(request  = Schema__Inventory__Load__Request(),
                     base_url = 'https://x', username='u', password='p')

        indices_called = sorted(call[1] for call in loader.http_client.bulk_calls)
        assert indices_called == ['sg-cf-inventory-2026-04-24',
                                   'sg-cf-inventory-2026-04-25',
                                   'sg-cf-inventory-2026-04-26']
        counts_per_day = sorted(call[2] for call in loader.http_client.bulk_calls)
        assert counts_per_day == [2, 2, 2]                                           # Each daily group carried 2 records

    def test_dry_run_skips_bulk_post(self):
        loader = build_loader()
        resp   = loader.load(request  = Schema__Inventory__Load__Request(prefix='cloudfront-realtime/2026/04/25/', dry_run=True),
                              base_url = 'https://1.2.3.4', username='u', password='p')
        assert resp.dry_run         is True
        assert resp.objects_scanned == 3
        assert resp.objects_indexed == 0
        assert loader.http_client.bulk_calls   == []                                # Bulk-post not called
        assert loader.kibana_client.ensure_calls == []                              # Data view ensure also skipped

    def test_empty_bucket_returns_zeros_cleanly(self):
        loader = build_loader(s3_pages=[[]])
        resp   = loader.load(request  = Schema__Inventory__Load__Request(prefix='cloudfront-realtime/2026/04/25/'),
                              base_url = 'https://1.2.3.4', username='u', password='p')
        assert resp.objects_scanned == 0
        assert resp.objects_indexed == 0
        assert resp.bytes_total     == 0
        assert resp.error_message   == ''

    def test_default_prefix_is_today_utc(self):                                     # Sanity-check default_prefix_for_today() shape
        prefix = default_prefix_for_today()
        today  = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        assert prefix == f'cloudfront-realtime/{today}/'

    def test_no_prefix_falls_through_to_today_default(self):                        # Empty Request.prefix → service resolves to today
        loader = build_loader(s3_pages=[[]])
        resp   = loader.load(request  = Schema__Inventory__Load__Request(),         # prefix='' all=False
                              base_url = 'https://x', username='u', password='p')
        assert resp.prefix_resolved == default_prefix_for_today()
        # Confirm the lister was called with the resolved prefix:
        assert loader.s3_lister.paginate_calls[0][1] == default_prefix_for_today()

    def test_all_flag_clears_prefix(self):                                          # --all means full-bucket scan; ignores any default
        loader = build_loader(s3_pages=[[]])
        resp   = loader.load(request  = Schema__Inventory__Load__Request(all=True),
                              base_url = 'https://x', username='u', password='p')
        assert resp.prefix_resolved == ''
        assert loader.s3_lister.paginate_calls[0][1] == ''

    def test_max_keys_passed_to_lister(self):                                       # CLI --max-keys flag flows through
        loader = build_loader(s3_pages=[[]])
        loader.load(request  = Schema__Inventory__Load__Request(max_keys=42),
                     base_url = 'https://x', username='u', password='p')
        assert loader.s3_lister.paginate_calls[0][2] == 42

    def test_run_id_auto_generated_when_empty(self):                                # Caller passes nothing → service generates via Run__Id__Generator
        loader = build_loader(s3_pages=[[]])
        resp   = loader.load(request  = Schema__Inventory__Load__Request(),
                              base_url = 'https://x', username='u', password='p')
        assert resp.run_id == '20260425T103042Z-cf-realtime-load-a3f2'              # Deterministic generator overrides pin the result

    def test_explicit_run_id_preserved(self):                                       # Caller-provided run_id must not be overwritten
        loader = build_loader(s3_pages=[[]])
        resp   = loader.load(request  = Schema__Inventory__Load__Request(run_id='my-test-run-id'),
                              base_url = 'https://x', username='u', password='p')
        assert resp.run_id == 'my-test-run-id'
