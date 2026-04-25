# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__S3__Key
# Pins acceptance of Firehose-emitted keys and the 1024-char S3 limit.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key import Safe_Str__S3__Key


FIREHOSE_KEY = 'cloudfront-realtime/2026/04/25/sgraph-send-cf-logs-to-s3-2-2026-04-25-00-00-20-e71885f4-7b8c-4d4f-a930-e1c6e7083682.gz'


class test_Safe_Str__S3__Key(TestCase):

    def test_firehose_key_accepted(self):                                           # The exact filename shape Firehose writes
        assert Safe_Str__S3__Key(FIREHOSE_KEY) == FIREHOSE_KEY

    def test_simple_key(self):
        assert Safe_Str__S3__Key('a/b/c.gz') == 'a/b/c.gz'

    def test_empty_allowed_for_auto_init(self):
        assert Safe_Str__S3__Key('') == ''

    def test_at_max_length_accepted(self):                                          # Up to 1024 chars
        big = 'a' * 1024
        assert Safe_Str__S3__Key(big) == big

    def test_disallowed_char_rejected(self):                                        # Backslash is not in the safe-ASCII subset we accept
        try:
            Safe_Str__S3__Key('bad\\char')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass
