# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Kibana__Saved_Objects__Client
# Covers find / export / import against canned Kibana responses. Subclasses
# request() instead of mocking — same pattern as test_bulk_post and
# test_elastic_probe.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

import requests

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Saved_Object__Type       import Enum__Saved_Object__Type
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client import Kibana__Saved_Objects__Client


def build_response(status_code: int, body: bytes) -> requests.Response:
    response             = requests.Response()
    response.status_code = status_code
    response._content    = body
    return response


class Recording__Client(Kibana__Saved_Objects__Client):                             # Records every call + returns a queue of canned responses
    captured_calls : list                                                            # [(method, url, headers, data), ...]
    canned_queue   : list                                                            # FIFO of requests.Response objects

    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        self.captured_calls.append((method, url, dict(headers or {}), data or b''))
        if not self.canned_queue:
            return build_response(200, b'{}')                                       # Default: empty success
        return self.canned_queue.pop(0)


class test_kibana_saved_objects_client__find(TestCase):

    def test_url_targets_find_endpoint_with_type_and_page_size(self):
        body   = json.dumps({'total': 0, 'saved_objects': []}).encode()
        client = Recording__Client(canned_queue=[build_response(200, body)])
        client.find('https://host', 'elastic', 'pw', Enum__Saved_Object__Type.DASHBOARD, page_size=50)
        method, url, headers, _ = client.captured_calls[0]
        assert method == 'GET'
        assert url    == 'https://host/api/saved_objects/_find?type=dashboard&per_page=50'
        assert headers.get('Authorization', '').startswith('Basic ')

    def test_parses_total_and_objects_from_payload(self):
        body = json.dumps({
            'total': 2,
            'saved_objects': [
                {'id': 'd1', 'type': 'dashboard', 'updated_at': '2026-04-25T10:00:00Z',
                 'attributes': {'title': 'Logs Overview'}},
                {'id': 'd2', 'type': 'dashboard', 'updated_at': '2026-04-25T11:00:00Z',
                 'attributes': {'title': 'Errors by Host'}},
            ],
        }).encode()
        client   = Recording__Client(canned_queue=[build_response(200, body)])
        response = client.find('https://host', 'elastic', 'pw', Enum__Saved_Object__Type.DASHBOARD)
        assert response.total == 2
        assert len(response.objects) == 2
        assert str(response.objects[0].title) == 'Logs Overview'
        assert str(response.objects[0].id)    == 'd1'
        assert str(response.objects[1].id)    == 'd2'
        assert response.http_status == 200
        assert str(response.error)  == ''

    def test_401_returns_error_with_body_snippet(self):
        client   = Recording__Client(canned_queue=[build_response(401, b'{"error":"unauthorized"}')])
        response = client.find('https://host', 'elastic', 'wrong', Enum__Saved_Object__Type.DASHBOARD)
        assert response.http_status == 401
        assert response.total       == 0
        assert 'HTTP 401'    in str(response.error)
        assert 'unauthorized' in str(response.error)

    def test_data_view_uses_index_pattern_type_string(self):                        # 8.x renamed the UI label but the API type is still index-pattern
        client = Recording__Client(canned_queue=[build_response(200, b'{"total":0,"saved_objects":[]}')])
        client.find('https://host', 'elastic', 'pw', Enum__Saved_Object__Type.DATA_VIEW)
        _, url, _, _ = client.captured_calls[0]
        assert 'type=index-pattern' in url


class test_kibana_saved_objects_client__export(TestCase):

    def test_export_posts_with_xsrf_header_and_deep_references(self):
        ndjson = b'{"id":"d1","type":"dashboard"}\n{"id":"v1","type":"visualization"}\n'
        client = Recording__Client(canned_queue=[build_response(200, ndjson)])
        body, status, err = client.export('https://host', 'elastic', 'pw',
                                          Enum__Saved_Object__Type.DASHBOARD,
                                          include_references_deep=True)
        method, url, headers, data = client.captured_calls[0]
        assert method == 'POST'
        assert url    == 'https://host/api/saved_objects/_export'
        assert headers.get('kbn-xsrf')       == 'true'
        assert headers.get('Content-Type')   == 'application/json'
        payload = json.loads(data.decode('utf-8'))
        assert payload['type']                 == ['dashboard']
        assert payload['includeReferencesDeep'] is True
        assert body   == ndjson
        assert status == 200
        assert err    == ''

    def test_export_skips_deep_when_disabled(self):
        client = Recording__Client(canned_queue=[build_response(200, b'')])
        client.export('https://host', 'elastic', 'pw',
                      Enum__Saved_Object__Type.DASHBOARD,
                      include_references_deep=False)
        _, _, _, data = client.captured_calls[0]
        payload = json.loads(data.decode('utf-8'))
        assert 'includeReferencesDeep' not in payload                               # Off by default — keeps the export narrow when caller asks for it

    def test_export_surfaces_http_error(self):
        client = Recording__Client(canned_queue=[build_response(403, b'{"error":"forbidden"}')])
        body, status, err = client.export('https://host', 'elastic', 'wrong',
                                          Enum__Saved_Object__Type.DASHBOARD)
        assert body   == b''
        assert status == 403
        assert 'HTTP 403' in err


class test_kibana_saved_objects_client__import(TestCase):

    def test_import_posts_multipart_with_overwrite_query(self):
        body  = json.dumps({'success': True, 'successCount': 3, 'errors': []}).encode()
        client = Recording__Client(canned_queue=[build_response(200, body)])
        ndjson = b'{"id":"d1","type":"dashboard","attributes":{"title":"x"}}\n'
        result = client.import_objects('https://host', 'elastic', 'pw', ndjson, overwrite=True)
        method, url, headers, data = client.captured_calls[0]
        assert method == 'POST'
        assert url    == 'https://host/api/saved_objects/_import?overwrite=true'
        assert headers.get('kbn-xsrf') == 'true'
        assert headers.get('Content-Type', '').startswith('multipart/form-data; boundary=')
        assert ndjson in data                                                       # The ndjson is wrapped in a multipart envelope but its bytes survive
        assert result.success       is True
        assert result.success_count == 3
        assert result.error_count   == 0
        assert result.http_status   == 200

    def test_import_summarises_per_item_errors(self):
        body  = json.dumps({
            'success': False,
            'successCount': 1,
            'errors': [
                {'id': 'd2', 'type': 'dashboard', 'error': {'type': 'conflict'}},
                {'id': 'd3', 'type': 'dashboard', 'error': {'type': 'missing_references'}},
            ],
        }).encode()
        client = Recording__Client(canned_queue=[build_response(200, body)])
        result = client.import_objects('https://host', 'elastic', 'pw', b'{}\n', overwrite=False)
        _, url, _, _ = client.captured_calls[0]
        assert url == 'https://host/api/saved_objects/_import'                      # No ?overwrite=true when off
        assert result.success       is False
        assert result.success_count == 1
        assert result.error_count   == 2
        assert 'conflict' in str(result.first_error)

    def test_import_surfaces_http_error_with_body_snippet(self):
        client = Recording__Client(canned_queue=[build_response(401, b'{"error":"unauthorized"}')])
        result = client.import_objects('https://host', 'elastic', 'wrong', b'{}\n')
        assert result.success     is False
        assert result.http_status == 401
        assert 'HTTP 401' in str(result.first_error)
