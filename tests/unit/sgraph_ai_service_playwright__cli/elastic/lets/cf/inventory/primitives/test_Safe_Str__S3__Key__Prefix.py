# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__S3__Key__Prefix
# Same character set as the full key but explicitly accepts the empty prefix
# (which means "list the entire bucket").
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix import Safe_Str__S3__Key__Prefix


class test_Safe_Str__S3__Key__Prefix(TestCase):

    def test_empty_means_full_bucket(self):
        assert Safe_Str__S3__Key__Prefix('') == ''

    def test_date_prefix(self):
        assert Safe_Str__S3__Key__Prefix('cloudfront-realtime/2026/04/25/') == 'cloudfront-realtime/2026/04/25/'

    def test_short_prefix_accepted(self):
        assert Safe_Str__S3__Key__Prefix('a') == 'a'

    def test_disallowed_char_rejected(self):
        try:
            Safe_Str__S3__Key__Prefix('weird?char')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
