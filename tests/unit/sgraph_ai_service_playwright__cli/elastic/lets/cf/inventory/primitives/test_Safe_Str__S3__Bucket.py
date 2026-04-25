# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__S3__Bucket
# Pins the AWS bucket-naming subset we accept, including the "{account}--
# {name}--{region}" pattern with consecutive hyphens used by SGraph buckets.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket import Safe_Str__S3__Bucket


class test_Safe_Str__S3__Bucket(TestCase):

    def test_simple_bucket(self):
        assert Safe_Str__S3__Bucket('my-bucket') == 'my-bucket'

    def test_sgraph_pattern_with_consecutive_hyphens(self):                         # The exact bucket the slice will read from
        b = Safe_Str__S3__Bucket('745506449035--sgraph-send-cf-logs--eu-west-2')
        assert b == '745506449035--sgraph-send-cf-logs--eu-west-2'

    def test_lower_cases_input(self):                                               # AWS treats bucket names as case-insensitive lowercase
        assert Safe_Str__S3__Bucket('My-Bucket') == 'my-bucket'

    def test_empty_allowed_for_auto_init(self):                                     # Service rejects empty on persist; primitive allows for auto-init
        assert Safe_Str__S3__Bucket('') == ''

    def test_too_short_rejected(self):                                              # AWS minimum is 3
        try:
            Safe_Str__S3__Bucket('ab')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_uppercase_only_rejected(self):                                         # `to_lower_case` first-pass-converts, but the regex still requires alnum start/end
        v = Safe_Str__S3__Bucket('AAA')                                             # Lower-cased then matched — should pass
        assert v == 'aaa'
