# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__S3__ETag
# Single-part ETags are 32 hex chars; multipart ETags add "-N". The CloudFront-
# realtime objects are always single-part (well under 5 MB) but the primitive
# accepts both shapes for future LETS sources.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__ETag import Safe_Str__S3__ETag


class test_Safe_Str__S3__ETag(TestCase):

    def test_single_part_md5(self):                                                 # Standard 32-char hex md5
        assert Safe_Str__S3__ETag('e71885f47b8c4d4fa930e1c6e7083682') == 'e71885f47b8c4d4fa930e1c6e7083682'

    def test_multipart_with_dash_part_count(self):                                  # md5-N shape
        assert Safe_Str__S3__ETag('abcdef0123456789abcdef0123456789-5') == 'abcdef0123456789abcdef0123456789-5'

    def test_uppercase_normalised_to_lower(self):                                   # AWS returns lowercase but normalise just in case
        assert Safe_Str__S3__ETag('E71885F47B8C4D4FA930E1C6E7083682') == 'e71885f47b8c4d4fa930e1c6e7083682'

    def test_empty_allowed_for_auto_init(self):
        assert Safe_Str__S3__ETag('') == ''

    def test_quotes_rejected(self):                                                 # AWS returns quoted; lister must strip before constructing
        try:
            Safe_Str__S3__ETag('"e71885f47b8c4d4fa930e1c6e7083682"')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_too_short_rejected(self):
        try:
            Safe_Str__S3__ETag('abc')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
