# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — parse_firehose_filename
# Pins the Firehose-emitted-key date extraction. Real keys from the
# 745506449035--sgraph-send-cf-logs--eu-west-2 bucket plus a few defensive
# rejections.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import parse_firehose_filename


REAL_KEY  = 'cloudfront-realtime/2026/04/25/sgraph-send-cf-logs-to-s3-2-2026-04-25-00-00-20-e71885f4-7b8c-4d4f-a930-e1c6e7083682.gz'
REAL_KEY2 = 'cloudfront-realtime/2026/04/25/sgraph-send-cf-logs-to-s3-2-2026-04-25-00-13-21-2d20b820-3487-452a-8b3a-16d210a69c7f.gz'


class test_parse_firehose_filename(TestCase):

    def test_real_firehose_key__early_morning(self):
        r = parse_firehose_filename(REAL_KEY)
        assert r['parsed'] is True
        assert r['year']   == 2026
        assert r['month']  == 4
        assert r['day']    == 25
        assert r['hour']   == 0
        assert r['minute'] == 0
        assert r['second'] == 20
        assert r['iso']    == '2026-04-25T00:00:20Z'

    def test_real_firehose_key__thirteen_minutes_in(self):                          # The second sample from the screenshot
        r = parse_firehose_filename(REAL_KEY2)
        assert r['parsed'] is True
        assert r['hour']   == 0
        assert r['minute'] == 13
        assert r['second'] == 21
        assert r['iso']    == '2026-04-25T00:13:21Z'

    def test_iso_format_zero_padded(self):                                          # Single-digit components must zero-pad
        r = parse_firehose_filename('foo-2026-01-02-03-04-05-deadbeef.gz')
        assert r['iso'] == '2026-01-02T03:04:05Z'

    def test_empty_key_returns_unparsed(self):
        r = parse_firehose_filename('')
        assert r['parsed'] is False
        assert r['year']   == 0
        assert r['iso']    == ''

    def test_non_matching_filename_returns_unparsed(self):                          # Without the embedded timestamp suffix
        r = parse_firehose_filename('cloudfront-realtime/2026/04/25/some-other-name.gz')
        assert r['parsed'] is False
        assert r['iso']    == ''

    def test_date_in_path_only_does_not_false_positive(self):                       # The path has 2026/04/25 but the basename does not — must NOT parse
        r = parse_firehose_filename('cloudfront-realtime/2026/04/25/random.gz')
        assert r['parsed'] is False

    def test_handles_extension_other_than_gz(self):                                 # Defensive: works for .ndjson etc. for future LETS sources
        r = parse_firehose_filename('foo-2026-04-25-12-34-56-deadbeef.ndjson')
        assert r['parsed'] is True
        assert r['iso']    == '2026-04-25T12:34:56Z'
