# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Manifest__Reader
# Pins the in-memory subclass behaviour: call-args captured, fixture docs
# returned, top_n cap respected.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader__In_Memory import Inventory__Manifest__Reader__In_Memory


def doc(etag: str, key: str = 'k.gz', size: int = 100) -> dict:
    return {'bucket': 'b', 'key': key, 'etag': etag, 'size_bytes': size, 'delivery_at': '2026-04-26T00:00:00.000Z'}


class test_Inventory__Manifest__Reader(TestCase):

    def test_starts_with_no_calls(self):
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[],
                                                          list_calls=[],
                                                          fixture_response=())
        assert reader.list_calls == []

    def test_returns_fixture_docs(self):
        docs_in = [doc('e1', 'a.gz'), doc('e2', 'b.gz')]
        reader  = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=docs_in,
                                                           list_calls=[],
                                                           fixture_response=())
        result, status, err = reader.list_unprocessed(base_url='https://x', username='u', password='p')
        assert len(result) == 2
        assert result[0]['etag'] == 'e1'
        assert status == 200
        assert err == ''

    def test_call_args_captured(self):
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[],
                                                          list_calls=[],
                                                          fixture_response=())
        reader.list_unprocessed(base_url='https://x', username='u', password='p', top_n=42)
        assert reader.list_calls == [('https://x', 42)]

    def test_top_n_caps_fixture(self):                                              # When fixture has more docs than top_n, the slice respects the cap
        docs_in = [doc(f'e{i}') for i in range(10)]
        reader  = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=docs_in,
                                                           list_calls=[],
                                                           fixture_response=())
        result, _, _ = reader.list_unprocessed(base_url='x', username='u', password='p', top_n=3)
        assert len(result) == 3

    def test_fixture_response_overrides(self):                                      # When fixture_response is set, ignore fixture_unprocessed_docs
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[doc('ignored')],
                                                          list_calls=[],
                                                          fixture_response=([], 503, 'cluster red'))
        result, status, err = reader.list_unprocessed(base_url='x', username='u', password='p')
        assert result == []
        assert status == 503
        assert 'cluster red' in err


# ─── list_processed_etags — fixture surface ──────────────────────────────────

class test_list_processed_etags__in_memory(TestCase):

    def test_returns_fixture_set(self):
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[], list_calls=[],
                                                          fixture_response=(),
                                                          fixture_processed_etags={'aa', 'bb', 'cc'},
                                                          processed_etag_calls=[])
        result = reader.list_processed_etags(base_url='https://x', username='u', password='p')
        assert result == {'aa', 'bb', 'cc'}

    def test_call_args_captured(self):
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[], list_calls=[],
                                                          fixture_response=(),
                                                          fixture_processed_etags=set(),
                                                          processed_etag_calls=[])
        reader.list_processed_etags(base_url='https://x', username='u', password='p', size_cap=500)
        assert reader.processed_etag_calls == [('https://x', 500)]


# ─── list_processed_etags — real implementation against canned ES response ───

import json
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader import Inventory__Manifest__Reader


class Fake__Response:
    def __init__(self, status_code, json_body=None, text=''):
        self.status_code = status_code
        self.text        = text
        self.json_body   = json_body
    def json(self):
        if self.json_body is None:
            raise ValueError('not JSON')
        return self.json_body


class Recording__HTTP__Client(Inventory__HTTP__Client):
    request_log    : list
    response_queue : list

    def request(self, method, url, *, headers=None, data=None):
        body_text = data.decode('utf-8') if isinstance(data, (bytes, bytearray)) else (data or '')
        self.request_log.append((method, url, body_text))
        if not self.response_queue:
            raise RuntimeError(f'no canned response for {method} {url}')
        return self.response_queue.pop(0)


class test_list_processed_etags__real(TestCase):

    def test_query_targets_inventory_pattern_with_processed_filter(self):           # Single source of truth: query sg-cf-inventory-* (NOT sg-cf-events-*) for content_processed=true
        es_response = {'aggregations': {'distinct_etags': {'buckets': [
            {'key': 'aa', 'doc_count': 1},
            {'key': 'bb', 'doc_count': 1},
        ]}}}
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(200, json_body=es_response)])
        reader = Inventory__Manifest__Reader(http_client=client)
        result = reader.list_processed_etags(base_url='https://x', username='u', password='p')

        assert result == {'aa', 'bb'}
        method, url, body_text = client.request_log[0]
        assert method == 'POST'
        assert '/_elastic/sg-cf-inventory-*/_search' in url
        body = json.loads(body_text)
        assert body['query'] == {'term': {'content_processed': True}}                # NOT querying sg-cf-events-*; NOT using source_etag
        assert body['aggs']['distinct_etags']['terms']['field'] == 'etag.keyword'

    def test_404_returns_empty_set(self):                                            # No inventory indices yet — empty set means "fetch everything"
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(404, text='no such index')])
        reader = Inventory__Manifest__Reader(http_client=client)
        assert reader.list_processed_etags(base_url='x', username='u', password='p') == set()

    def test_request_exception_returns_empty_set(self):                              # Network drop → fall back to "fetch everything"
        class Boom__Client(Inventory__HTTP__Client):
            def request(self, *a, **k):
                raise ConnectionError('nginx unreachable')
        reader = Inventory__Manifest__Reader(http_client=Boom__Client())
        assert reader.list_processed_etags(base_url='x', username='u', password='p') == set()

    def test_size_cap_reflected_in_query(self):
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(200, json_body={'aggregations': {'distinct_etags': {'buckets': []}}})])
        reader = Inventory__Manifest__Reader(http_client=client)
        reader.list_processed_etags(base_url='x', username='u', password='p', size_cap=42)
        body = json.loads(client.request_log[0][2])
        assert body['aggs']['distinct_etags']['terms']['size'] == 42
