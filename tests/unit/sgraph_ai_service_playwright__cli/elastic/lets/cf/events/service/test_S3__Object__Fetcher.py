# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — S3__Object__Fetcher
# Drives the fetcher via its in-memory subclass.  Pins call-arg capture and
# the (bucket, key) lookup precedence.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher__In_Memory import S3__Object__Fetcher__In_Memory


class test_S3__Object__Fetcher(TestCase):

    def test_returns_canned_bytes_by_key(self):                                     # Single-bucket convenience: lookup by key only
        fetcher = S3__Object__Fetcher__In_Memory(fixture_objects = {'k.gz': b'\x1f\x8bhello'},
                                                   get_calls       = []                       )
        body = fetcher.get_object_bytes(bucket='b', key='k.gz')
        assert body == b'\x1f\x8bhello'

    def test_call_args_captured(self):                                              # (bucket, key, region) tuple shape
        fetcher = S3__Object__Fetcher__In_Memory(fixture_objects = {'k.gz': b'x'},
                                                   get_calls       = []            )
        fetcher.get_object_bytes(bucket='my-bucket', key='k.gz', region='eu-west-2')
        assert fetcher.get_calls == [('my-bucket', 'k.gz', 'eu-west-2')]

    def test_bucket_key_tuple_takes_precedence(self):                               # When both ('b', 'k') and 'k' exist, the tuple wins
        fetcher = S3__Object__Fetcher__In_Memory(
            fixture_objects = {('b', 'k'): b'tuple-wins',
                               'k'       : b'key-only'   },
            get_calls       = [])
        body = fetcher.get_object_bytes(bucket='b', key='k')
        assert body == b'tuple-wins'

    def test_missing_key_raises(self):                                              # Tests should pre-populate fixture_objects; absent → fail loud
        fetcher = S3__Object__Fetcher__In_Memory(fixture_objects = {}, get_calls = [])
        try:
            fetcher.get_object_bytes(bucket='b', key='missing.gz')
            assert False, 'expected KeyError'
        except KeyError as exc:
            assert 'missing.gz' in str(exc)
