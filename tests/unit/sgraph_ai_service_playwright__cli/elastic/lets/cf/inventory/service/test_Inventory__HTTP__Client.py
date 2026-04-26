# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__HTTP__Client
# The In_Memory subclass overrides bulk_post_with_id wholesale, so these tests
# pin behaviour at the override seam: empty docs short-circuit, the call
# arguments are captured, and fixture overrides flow through unchanged.
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.collections.List__Schema__S3__Object__Record import List__Schema__S3__Object__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__S3__Object__Record import Schema__S3__Object__Record

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory


def make_records(n: int) -> List__Schema__S3__Object__Record:
    lst = List__Schema__S3__Object__Record()
    for i in range(n):
        lst.append(Schema__S3__Object__Record(etag=f'{i:032x}'))                    # 32-hex etag — unique per doc
    return lst


class test_Inventory__HTTP__Client(TestCase):

    def test_call_args_captured(self):                                              # Confirms (base_url, index, count, id_field) tuple shape
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=())
        client.bulk_post_with_id(base_url='https://1.2.3.4', username='u', password='p',
                                  index='sg-cf-inventory-2026-04-25', docs=make_records(3),
                                  id_field='etag')
        assert client.bulk_calls == [('https://1.2.3.4', 'sg-cf-inventory-2026-04-25', 3, 'etag')]

    def test_default_fixture_returns_all_created(self):                             # Fixture-mode default: every doc reported as created, HTTP 200
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=())
        created, updated, failed, status, err = client.bulk_post_with_id(
            base_url='https://1.2.3.4', username='u', password='p',
            index='sg-cf-inventory-2026-04-25', docs=make_records(5))
        assert (created, updated, failed, status, err) == (5, 0, 0, 200, '')

    def test_fixture_override_propagates(self):                                     # Tests that need to simulate failure inject their own tuple
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[],
                                                     fixture_response=(0, 0, 5, 503, 'HTTP 503: ES temporarily down'))
        created, updated, failed, status, err = client.bulk_post_with_id(
            base_url='https://1.2.3.4', username='u', password='p',
            index='sg-cf-inventory-2026-04-25', docs=make_records(5))
        assert created == 0
        assert failed  == 5
        assert status  == 503
        assert 'HTTP 503' in err

    def test_empty_docs_short_circuit(self):                                        # Real implementation returns (0, 0, 0, 0, '') without calling request()
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=())
        result = client.bulk_post_with_id(base_url='https://x', username='u', password='p',
                                           index='i', docs=List__Schema__S3__Object__Record())
        assert result == (0, 0, 0, 200, '')                                         # In_Memory returns its default with len(docs)=0
        assert client.bulk_calls == [('https://x', 'i', 0, 'etag')]


class test_delete_indices_by_pattern(TestCase):

    def test_call_args_captured(self):                                              # (base_url, pattern) tuple shape
        client = Inventory__HTTP__Client__In_Memory(delete_pattern_calls=[],
                                                     fixture_delete_pattern_response=())
        client.delete_indices_by_pattern(base_url='https://1.2.3.4', username='u', password='p',
                                          pattern='sg-cf-inventory-*')
        assert client.delete_pattern_calls == [('https://1.2.3.4', 'sg-cf-inventory-*')]

    def test_default_returns_zero_no_error(self):                                   # Fixture-mode default: nothing to delete, HTTP 200
        client = Inventory__HTTP__Client__In_Memory(delete_pattern_calls=[],
                                                     fixture_delete_pattern_response=())
        count, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p', pattern='sg-cf-inventory-*')
        assert (count, status, err) == (0, 200, '')

    def test_fixture_override_propagates(self):                                     # Tests that simulate "3 indices dropped" inject their own tuple
        client = Inventory__HTTP__Client__In_Memory(delete_pattern_calls=[],
                                                     fixture_delete_pattern_response=(3, 200, ''))
        count, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p', pattern='sg-cf-inventory-*')
        assert count == 3
        assert status == 200

    def test_fixture_error_propagates(self):
        client = Inventory__HTTP__Client__In_Memory(delete_pattern_calls=[],
                                                     fixture_delete_pattern_response=(0, 503, 'cluster red'))
        count, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p', pattern='sg-cf-inventory-*')
        assert count == 0
        assert status == 503
        assert 'cluster red' in err


# ─── regression tests against the REAL implementation ────────────────────────
# The In_Memory subclass overrides delete_indices_by_pattern wholesale, so it
# can't catch the wildcard-DELETE bug Elasticsearch raises with its default
# `action.destructive_requires_name=true` setting (HTTP 400 "Wildcard
# expressions or all indices are not allowed").  These tests subclass
# Inventory__HTTP__Client directly and override the lower-level request()
# seam so we exercise the real list-then-delete-by-name path.

class Fake__Response:                                                               # Minimal interface mirroring requests.Response — no requests dependency
    def __init__(self, status_code, json_body=None, text=''):
        self.status_code = status_code
        self.text        = text
        self.json_body   = json_body

    def json(self):
        if self.json_body is None:
            raise ValueError('not JSON')
        return self.json_body


class Inventory__HTTP__Client__Recording_Requests(Inventory__HTTP__Client__In_Memory.__bases__[0]):  # i.e. Inventory__HTTP__Client (the real class)
    request_log    : list                                                            # [(method, url), ...]
    response_queue : list                                                            # FIFO of Fake__Response

    def request(self, method, url, *, headers=None, data=None):
        self.request_log.append((method, url))
        if not self.response_queue:
            raise RuntimeError(f'no canned response for {method} {url}')
        return self.response_queue.pop(0)


class test_real_delete_indices_by_pattern(TestCase):

    def test_lists_then_deletes_each_index_by_name(self):                           # Regression: must NOT issue DELETE /_elastic/sg-cf-inventory-*
        client = Inventory__HTTP__Client__Recording_Requests(
            request_log    = [],
            response_queue = [
                Fake__Response(200, json_body=[{'index': 'sg-cf-inventory-2026-04-25'},
                                                {'index': 'sg-cf-inventory-2026-04-26'}]),  # _cat/indices
                Fake__Response(200, json_body={'acknowledged': True}),               # DELETE first
                Fake__Response(200, json_body={'acknowledged': True}),               # DELETE second
            ])
        deleted, status, err = client.delete_indices_by_pattern(
            base_url='https://1.2.3.4', username='u', password='p',
            pattern='sg-cf-inventory-*')
        assert deleted == 2
        assert status  == 200
        assert err     == ''
        # 1 list + 2 deletes
        methods = [m for m, _ in client.request_log]
        assert methods == ['GET', 'DELETE', 'DELETE']
        # CRITICAL: DELETE URLs use the EXACT index names, not the wildcard
        delete_urls = [url for m, url in client.request_log if m == 'DELETE']
        assert any('sg-cf-inventory-2026-04-25' in url for url in delete_urls)
        assert any('sg-cf-inventory-2026-04-26' in url for url in delete_urls)
        assert not any('*' in url for url in delete_urls)

    def test_no_indices_means_no_deletes(self):                                     # Listing returned [], so DELETE must not be called at all
        client = Inventory__HTTP__Client__Recording_Requests(
            request_log    = [],
            response_queue = [Fake__Response(200, json_body=[])])
        deleted, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p',
            pattern='sg-cf-inventory-*')
        assert deleted == 0
        assert err     == ''
        methods = [m for m, _ in client.request_log]
        assert methods == ['GET']

    def test_per_index_404_tolerated_count_only_real_drops(self):                   # Race: someone deleted one index between our list and our delete
        client = Inventory__HTTP__Client__Recording_Requests(
            request_log    = [],
            response_queue = [
                Fake__Response(200, json_body=[{'index': 'a'}, {'index': 'b'}]),
                Fake__Response(404),                                                 # 'a' already gone
                Fake__Response(200, json_body={'acknowledged': True}),               # 'b' deleted
            ])
        deleted, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p',
            pattern='sg-cf-inventory-*')
        assert deleted == 1                                                          # Only 'b' was actually dropped
        assert err     == ''                                                         # 404 is not an error

    def test_per_index_400_recorded_as_first_error_keeps_going(self):
        client = Inventory__HTTP__Client__Recording_Requests(
            request_log    = [],
            response_queue = [
                Fake__Response(200, json_body=[{'index': 'a'}, {'index': 'b'}]),
                Fake__Response(400, text='something broke'),                         # 'a' rejected
                Fake__Response(200, json_body={'acknowledged': True}),               # 'b' deleted
            ])
        deleted, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p',
            pattern='sg-cf-inventory-*')
        assert deleted == 1                                                          # Only 'b' was dropped
        assert 'delete a HTTP 400' in err                                            # First error captured
        assert 'something broke'   in err

    def test_list_404_returns_clean_zero(self):                                     # Pattern matches nothing — no error, no work
        client = Inventory__HTTP__Client__Recording_Requests(
            request_log    = [],
            response_queue = [Fake__Response(404, text='no such index')])
        deleted, status, err = client.delete_indices_by_pattern(
            base_url='https://x', username='u', password='p',
            pattern='sg-cf-inventory-*')
        assert deleted == 0
        assert status  == 404
        assert err     == ''
