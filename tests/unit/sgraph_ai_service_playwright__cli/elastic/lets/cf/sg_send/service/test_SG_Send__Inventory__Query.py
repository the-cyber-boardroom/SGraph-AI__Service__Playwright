# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — SG_Send__Inventory__Query
# Drives the real list_files_for_date implementation against a recording HTTP
# client (canned responses, no requests / no Elastic).  Asserts:
#   - Body shape (term clauses for year/month/day/+hour, sort, _source)
#   - Hit unpacking (rows preserve order, types, processed flag)
#   - 404 → empty rows + empty error
#   - HTTP error → empty rows + error message
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__Inventory__Query import SG_Send__Inventory__Query


class Fake__Response:                                                                # Minimal requests.Response surface — no requests dep
    def __init__(self, status_code, json_body=None, text=''):
        self.status_code = status_code
        self.text        = text
        self.json_body   = json_body

    def json(self):
        if self.json_body is None:
            raise ValueError('not JSON')
        return self.json_body


class Recording__HTTP__Client(Inventory__HTTP__Client):
    request_log    : list                                                            # [(method, url, body_text), ...]
    response_queue : list                                                            # FIFO of Fake__Response

    def request(self, method, url, *, headers=None, data=None):
        body_text = data.decode('utf-8') if isinstance(data, (bytes, bytearray)) else (data or '')
        self.request_log.append((method, url, body_text))
        if not self.response_queue:
            raise RuntimeError(f'no canned response for {method} {url}')
        return self.response_queue.pop(0)


def make_es_response(rows):                                                          # Wrap a list of `_source` dicts into the ES `hits.hits` envelope
    return {'hits': {'hits': [{'_source': r} for r in rows]}}


class test_list_files_for_date(TestCase):

    def test_body_carries_year_month_day_terms_and_sort(self):
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(200, json_body=make_es_response([]))])
        query  = SG_Send__Inventory__Query(http_client=client)
        rows, status, err = query.list_files_for_date(base_url='https://x', username='u', password='p',
                                                        year=2026, month=4, day=25)
        assert rows == []
        assert status == 200
        assert err    == ''

        method, url, body_text = client.request_log[0]
        assert method == 'POST'
        assert '/_elastic/sg-cf-inventory-*/_search' in url
        body = json.loads(body_text)
        must_terms = body['query']['bool']['must']
        assert {'term': {'delivery_year' : 2026}} in must_terms
        assert {'term': {'delivery_month':    4}} in must_terms
        assert {'term': {'delivery_day'  :   25}} in must_terms
        # No hour clause when hour is None
        assert all('delivery_hour' not in str(c) for c in must_terms)
        # Sort by delivery_at asc
        assert body['sort'] == [{'delivery_at': {'order': 'asc'}}]

    def test_hour_clause_added_when_hour_provided(self):
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(200, json_body=make_es_response([]))])
        query  = SG_Send__Inventory__Query(http_client=client)
        query.list_files_for_date(base_url='https://x', username='u', password='p',
                                   year=2026, month=4, day=25, hour=14)
        body = json.loads(client.request_log[0][2])
        assert {'term': {'delivery_hour': 14}} in body['query']['bool']['must']

    def test_hits_unpacked_into_typed_rows(self):
        es_rows = [
            {'key'              : 'cloudfront-realtime/2026/04/25/14/file-A.gz',
              'size_bytes'      : 1234,
              'etag'            : 'abcd1234',
              'delivery_at'     : '2026-04-25T14:30:17.167Z',
              'delivery_hour'   : 14,
              'delivery_minute' : 30,
              'content_processed'      : True,
              'content_extract_run_id' : 'run-foo'},
            {'key'              : 'cloudfront-realtime/2026/04/25/14/file-B.gz',
              'size_bytes'      : 5678,
              'etag'            : 'effe5678',
              'delivery_at'     : '2026-04-25T14:45:00.001Z',
              'delivery_hour'   : 14,
              'delivery_minute' : 45,
              'content_processed'      : False,
              'content_extract_run_id' : ''},
        ]
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(200, json_body=make_es_response(es_rows))])
        query  = SG_Send__Inventory__Query(http_client=client)
        rows, status, err = query.list_files_for_date(base_url='https://x', username='u', password='p',
                                                        year=2026, month=4, day=25, hour=14)
        assert status == 200 and err == ''
        assert len(rows) == 2
        assert rows[0]['key']               == 'cloudfront-realtime/2026/04/25/14/file-A.gz'
        assert rows[0]['size_bytes']        == 1234
        assert rows[0]['etag']              == 'abcd1234'
        assert rows[0]['delivery_at']       == '2026-04-25T14:30:17.167Z'
        assert rows[0]['delivery_hour']     == 14
        assert rows[0]['delivery_minute']   == 30
        assert rows[0]['content_processed']      is True
        assert rows[0]['content_extract_run_id'] == 'run-foo'
        assert rows[1]['content_processed']      is False
        assert rows[1]['content_extract_run_id'] == ''

    def test_404_returns_empty_rows_no_error(self):                                  # No inventory indices yet
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(404, text='no such index')])
        query  = SG_Send__Inventory__Query(http_client=client)
        rows, status, err = query.list_files_for_date(base_url='https://x', username='u', password='p',
                                                        year=2026, month=4, day=25)
        assert rows == []
        assert status == 404
        assert err    == ''

    def test_500_returns_empty_rows_with_error(self):
        client = Recording__HTTP__Client(request_log=[],
                                          response_queue=[Fake__Response(503, text='cluster red')])
        query  = SG_Send__Inventory__Query(http_client=client)
        rows, status, err = query.list_files_for_date(base_url='https://x', username='u', password='p',
                                                        year=2026, month=4, day=25)
        assert rows == []
        assert status == 503
        assert 'HTTP 503' in err
        assert 'cluster red' in err

    def test_request_exception_caught(self):                                         # Network drop / DNS failure
        class Boom__Client(Inventory__HTTP__Client):
            def request(self, *a, **k):
                raise ConnectionError('nginx unreachable')
        query = SG_Send__Inventory__Query(http_client=Boom__Client())
        rows, status, err = query.list_files_for_date(base_url='https://x', username='u', password='p',
                                                        year=2026, month=4, day=25)
        assert rows == []
        assert status == 0
        assert 'search error' in err
