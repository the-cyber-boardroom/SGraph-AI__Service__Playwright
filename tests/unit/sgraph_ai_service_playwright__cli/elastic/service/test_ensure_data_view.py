# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Kibana__Saved_Objects__Client.ensure_data_view
# Pins idempotent data-view creation: when a data view with the requested
# title already exists, return its id with created=False; when not, POST
# /api/data_views/data_view and return the new id with created=True.
# Real subclass that returns a queue of canned requests.Response objects —
# no mocks. Same pattern as test_kibana_saved_objects_client.py.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

import requests

from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client import Kibana__Saved_Objects__Client


def build_response(status_code: int, body: bytes) -> requests.Response:
    response             = requests.Response()
    response.status_code = status_code
    response._content    = body
    return response


class Recording__Client(Kibana__Saved_Objects__Client):
    captured_calls : list                                                            # [(method, url, headers, data), ...]
    canned_queue   : list                                                            # FIFO of requests.Response

    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        self.captured_calls.append((method, url, dict(headers or {}), data or b''))
        if not self.canned_queue:
            return build_response(200, b'{}')
        return self.canned_queue.pop(0)


class test_ensure_data_view(TestCase):

    def test_creates_when_no_existing_data_view_matches(self):
        find_body  = json.dumps({'total': 0, 'saved_objects': []}).encode()
        create_body = json.dumps({'data_view': {'id': 'dv-uuid-1', 'title': 'sg-synthetic'}}).encode()
        client = Recording__Client(canned_queue=[build_response(200, find_body),
                                                  build_response(200, create_body)])
        result = client.ensure_data_view('https://host', 'elastic', 'pw', 'sg-synthetic', 'timestamp')
        assert str(result.id)         == 'dv-uuid-1'
        assert result.created          is True
        assert result.http_status      == 200
        assert str(result.error)       == ''
        # Find first, create second
        assert len(client.captured_calls) == 2
        assert client.captured_calls[0][0] == 'GET'
        assert '/api/saved_objects/_find?type=index-pattern' in client.captured_calls[0][1]
        assert client.captured_calls[1][0] == 'POST'
        assert client.captured_calls[1][1] == 'https://host/api/data_views/data_view'
        # POST body has the index name and time field
        posted = json.loads(client.captured_calls[1][3].decode('utf-8'))
        assert posted['data_view']['title']         == 'sg-synthetic'
        assert posted['data_view']['name']          == 'sg-synthetic'
        assert posted['data_view']['timeFieldName'] == 'timestamp'
        # CSRF header was set
        assert client.captured_calls[1][2].get('kbn-xsrf') == 'true'

    def test_skips_creation_when_data_view_already_exists(self):
        find_body = json.dumps({
            'total': 1,
            'saved_objects': [{'id': 'existing-uuid', 'type': 'index-pattern',
                                'attributes': {'title': 'sg-synthetic'}}],
        }).encode()
        client = Recording__Client(canned_queue=[build_response(200, find_body)])
        result = client.ensure_data_view('https://host', 'elastic', 'pw', 'sg-synthetic', 'timestamp')
        assert str(result.id)    == 'existing-uuid'
        assert result.created    is False
        assert str(result.error) == ''
        # Only one call — no POST
        assert len(client.captured_calls) == 1

    def test_other_titles_in_listing_do_not_match(self):                             # The title comparison is exact — "logs-foo" must not satisfy a request for "sg-synthetic"
        find_body  = json.dumps({
            'total': 2,
            'saved_objects': [{'id': 'a', 'type': 'index-pattern', 'attributes': {'title': 'logs-foo'}},
                               {'id': 'b', 'type': 'index-pattern', 'attributes': {'title': 'metrics-*'}}],
        }).encode()
        create_body = json.dumps({'data_view': {'id': 'dv-new', 'title': 'sg-synthetic'}}).encode()
        client = Recording__Client(canned_queue=[build_response(200, find_body),
                                                  build_response(200, create_body)])
        result = client.ensure_data_view('https://host', 'elastic', 'pw', 'sg-synthetic', 'timestamp')
        assert result.created is True
        assert str(result.id) == 'dv-new'

    def test_find_401_surfaces_error_without_post(self):
        client = Recording__Client(canned_queue=[build_response(401, b'{"error":"unauthorized"}')])
        result = client.ensure_data_view('https://host', 'elastic', 'wrong', 'sg-synthetic', 'timestamp')
        assert result.created     is False
        assert result.http_status == 401
        assert 'HTTP 401' in str(result.error)
        # Only the find call — no POST attempt when auth already failed
        assert len(client.captured_calls) == 1

    def test_create_failure_surfaces_body_snippet(self):
        find_body  = json.dumps({'total': 0, 'saved_objects': []}).encode()
        client = Recording__Client(canned_queue=[build_response(200, find_body),
                                                  build_response(409, b'{"error":"conflict"}')])
        result = client.ensure_data_view('https://host', 'elastic', 'pw', 'sg-synthetic', 'timestamp')
        assert result.created     is False
        assert result.http_status == 409
        assert 'HTTP 409' in str(result.error)
