# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__HTTP__Client.bulk_post NDJSON body
# Regression for a .join()-over-dicts TypeError: Type_Safe's .json() returns
# a dict, not a string, so each document line must be wrapped in json.dumps()
# before being joined into the NDJSON body. This test captures the actual
# bytes sent and parses them back to confirm each line is a valid JSON object.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

import requests                                                                     # Real module — we subclass response, no mocks

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Log__Document   import List__Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Log__Level               import Enum__Log__Level
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Log__Document        import Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client        import Elastic__HTTP__Client


class Capturing__Client(Elastic__HTTP__Client):                                     # Subclass that records what request() was called with
    last_method  : str   = ''
    last_url     : str   = ''
    last_headers : dict  = None
    last_body    : bytes = b''

    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        self.last_method  = method
        self.last_url     = url
        self.last_headers = dict(headers or {})
        self.last_body    = data or b''
        response          = requests.Response()
        response.status_code = 200
        response._content    = b'{"errors":false,"items":[]}'
        return response


def build_doc(message: str) -> Schema__Log__Document:
    return Schema__Log__Document(timestamp   = '2026-01-01T00:00:00.000Z',
                                 level       = Enum__Log__Level.INFO     ,
                                 service     = 'test-svc'                 ,
                                 host        = 'test-host'                ,
                                 user        = 'alice'                    ,
                                 message     = message                    ,
                                 duration_ms = 1                          )


class test_bulk_post(TestCase):

    def test_body_is_valid_ndjson_with_alternating_action_and_doc_lines(self):
        docs = List__Schema__Log__Document()
        docs.append(build_doc('first message'))
        docs.append(build_doc('second message'))

        client = Capturing__Client()
        posted, failed, status, err = client.bulk_post(base_url = 'https://host.example' ,
                                                       username = 'elastic'              ,
                                                       password = 'pw'                   ,
                                                       index    = 'sg-synthetic'          ,
                                                       docs     = docs                    )

        assert posted == 2
        assert failed == 0
        assert status == 200
        assert err    == ''
        assert client.last_method == 'POST'
        assert client.last_url    == 'https://host.example/_elastic/_bulk'
        assert client.last_headers.get('Content-Type') == 'application/x-ndjson'

        body = client.last_body.decode('utf-8')                                     # Final trailing \n is required by _bulk — split and drop the empty trailing element
        lines = body.split('\n')
        assert lines[-1] == ''                                                      # Trailing newline present
        lines = lines[:-1]
        assert len(lines) == 4                                                      # 2 action lines + 2 source lines

        for line in lines:                                                          # Every line is a standalone JSON object (not a dict literal, not the string "None")
            parsed = json.loads(line)
            assert isinstance(parsed, dict)

        # Action lines target the right index
        assert json.loads(lines[0]) == {'index': {'_index': 'sg-synthetic'}}
        assert json.loads(lines[2]) == {'index': {'_index': 'sg-synthetic'}}
        # Doc lines carry the payload
        doc_0 = json.loads(lines[1])
        doc_1 = json.loads(lines[3])
        assert doc_0['message'] == 'first message'
        assert doc_1['message'] == 'second message'
        assert doc_0['level']   == 'INFO'
        assert 'timestamp'      in doc_0

    def test_empty_docs_returns_zero_zero_without_http_call(self):
        client = Capturing__Client()
        posted, failed, status, err = client.bulk_post('https://host', 'elastic', 'pw', 'idx',
                                                       List__Schema__Log__Document())
        assert (posted, failed, status, err) == (0, 0, 0, '')
        assert client.last_method    == ''                                          # request() never called


class Rejecting__Client(Capturing__Client):                                         # Returns HTTP 401 to mimic SG_ELASTIC_PASSWORD mismatch
    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        super().request(method, url, headers=headers, data=data)
        response = requests.Response()
        response.status_code = 401
        response._content    = b'{"error":"unauthorized","reason":"basic auth failed"}'
        return response


class test_bulk_post__http_error_surfacing(TestCase):

    def test_unauthorized_returns_status_and_body_snippet(self):
        # Regression for "posted 0, failed 10000, no reason shown". A 401
        # from _bulk must surface as (0, all_failed, 401, "HTTP 401: ...body...")
        # so Schema__Elastic__Seed__Response can include last_http_status and
        # the CLI can tell the user to re-check SG_ELASTIC_PASSWORD.
        docs = List__Schema__Log__Document()
        for i in range(3):
            docs.append(build_doc(f'msg {i}'))

        client = Rejecting__Client()
        posted, failed, status, err = client.bulk_post('https://host', 'elastic', 'wrong',
                                                       'sg-synthetic', docs)
        assert posted == 0
        assert failed == 3
        assert status == 401
        assert 'HTTP 401' in err
        assert 'unauthorized' in err
