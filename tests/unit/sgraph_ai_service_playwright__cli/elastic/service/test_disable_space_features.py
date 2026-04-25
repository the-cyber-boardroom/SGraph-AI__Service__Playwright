# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Kibana__Saved_Objects__Client.disable_space_features
# Pins the GET-then-PUT contract that hides Observability / Security solution
# groups from the Kibana side-nav. Real subclass returning canned Response
# objects — no mocks.
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
    captured_calls : list
    canned_queue   : list

    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        self.captured_calls.append((method, url, dict(headers or {}), data or b''))
        if not self.canned_queue:
            return build_response(200, b'{}')
        return self.canned_queue.pop(0)


class test_disable_space_features(TestCase):

    def test_get_then_put_with_disabled_features_replacing_existing(self):
        existing_space = {
            'id'              : 'default',
            'name'            : 'Default',
            'description'     : 'This is your default space',
            'disabledFeatures': []                                                  # No features disabled before our call
        }
        client = Recording__Client(canned_queue=[build_response(200, json.dumps(existing_space).encode()),
                                                  build_response(200, b'{}')])
        ok, status, err = client.disable_space_features('https://host', 'elastic', 'pw',
                                                         space_id='default',
                                                         features=['observability', 'siem', 'fleet'])
        assert ok      is True
        assert status  == 200
        assert err     == ''
        # Two calls: GET then PUT
        assert len(client.captured_calls) == 2
        assert client.captured_calls[0][0] == 'GET'
        assert client.captured_calls[0][1] == 'https://host/api/spaces/space/default'
        assert client.captured_calls[1][0] == 'PUT'
        assert client.captured_calls[1][1] == 'https://host/api/spaces/space/default'
        # PUT body preserves name+description from GET, sets disabledFeatures
        put_body = json.loads(client.captured_calls[1][3].decode('utf-8'))
        assert put_body['id']               == 'default'
        assert put_body['name']             == 'Default'
        assert put_body['description']      == 'This is your default space'
        assert put_body['disabledFeatures'] == ['observability', 'siem', 'fleet']
        # CSRF header set on PUT
        assert client.captured_calls[1][2].get('kbn-xsrf') == 'true'

    def test_default_features_cover_observability_security_fleet(self):              # The whole point: when caller passes no list, we apply our own opinionated default
        existing_space = {'id': 'default', 'name': 'Default', 'disabledFeatures': []}
        client = Recording__Client(canned_queue=[build_response(200, json.dumps(existing_space).encode()),
                                                  build_response(200, b'{}')])
        client.disable_space_features('https://host', 'elastic', 'pw')
        put_body = json.loads(client.captured_calls[1][3].decode('utf-8'))
        # Spot-check the categories the user explicitly asked us to hide
        assert 'observability' in put_body['disabledFeatures']
        assert 'siem'          in put_body['disabledFeatures']
        assert 'fleet'         in put_body['disabledFeatures']
        assert 'ml'            in put_body['disabledFeatures']

    def test_get_failure_surfaces_without_put(self):
        client = Recording__Client(canned_queue=[build_response(401, b'{"error":"unauthorized"}')])
        ok, status, err = client.disable_space_features('https://host', 'elastic', 'wrong')
        assert ok       is False
        assert status   == 401
        assert 'HTTP 401' in err
        # No PUT attempted when the GET already failed
        assert len(client.captured_calls) == 1

    def test_put_failure_surfaces_body_snippet(self):
        existing_space = {'id': 'default', 'name': 'Default', 'disabledFeatures': []}
        client = Recording__Client(canned_queue=[build_response(200, json.dumps(existing_space).encode()),
                                                  build_response(403, b'{"error":"forbidden"}')])
        ok, status, err = client.disable_space_features('https://host', 'elastic', 'low-priv-user')
        assert ok       is False
        assert status   == 403
        assert 'HTTP 403' in err
