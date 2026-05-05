# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: test_Routes__Firefox__Credentials
# Tests for PUT /api/specs/firefox/{node_id}/credentials
#      and PUT /api/specs/firefox/{node_id}/mitm-script
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from fastapi.testclient                                                             import TestClient
from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sg_compute_specs.firefox.api.routes.Routes__Firefox__Stack                    import Routes__Firefox__Stack
from sg_compute_specs.firefox.schemas.Schema__Firefox__Credentials__Response       import Schema__Firefox__Credentials__Response
from sg_compute_specs.firefox.schemas.Schema__Firefox__Mitm__Script__Response      import Schema__Firefox__Mitm__Script__Response
from sg_compute_specs.firefox.service.Firefox__Service                             import Firefox__Service


class _Fake__Firefox__Service(Firefox__Service):

    def set_credentials(self, region, node_id, username, password):
        return Schema__Firefox__Credentials__Response(
            node_id = node_id,
            updated = True   ,
            message = f'credentials updated for {node_id}')

    def upload_mitm_script(self, region, node_id, script_content):
        return Schema__Firefox__Mitm__Script__Response(
            node_id  = node_id,
            uploaded = True   ,
            message  = f'script uploaded ({len(script_content)} bytes)')


class test_Routes__Firefox__Credentials(TestCase):

    def setUp(self):
        fast_api  = Fast_API()
        fast_api.add_routes(Routes__Firefox__Stack, service=_Fake__Firefox__Service())
        self.client = TestClient(fast_api.app())

    def test_set_credentials_returns_200(self):
        r = self.client.put('/firefox/my-node/credentials',
                            json={'username': 'admin', 'password': 'secret123'})
        assert r.status_code == 200
        data = r.json()
        assert data['node_id'] == 'my-node'
        assert data['updated'] is True

    def test_set_credentials_missing_username_returns_422(self):
        r = self.client.put('/firefox/my-node/credentials',
                            json={'password': 'secret123'})
        assert r.status_code == 422

    def test_set_credentials_missing_password_returns_422(self):
        r = self.client.put('/firefox/my-node/credentials',
                            json={'username': 'admin'})
        assert r.status_code == 422

    def test_upload_mitm_script_returns_200(self):
        script = 'def request(flow): pass'
        r      = self.client.put('/firefox/my-node/mitm-script',
                                 json={'content': script})
        assert r.status_code == 200
        data = r.json()
        assert data['node_id']  == 'my-node'
        assert data['uploaded'] is True

    def test_upload_mitm_script_empty_content_returns_422(self):
        r = self.client.put('/firefox/my-node/mitm-script', json={'content': ''})
        assert r.status_code == 422

    def test_response_schema_shape(self):
        r = self.client.put('/firefox/my-node/credentials',
                            json={'username': 'u', 'password': 'p'})
        assert r.status_code == 200
        assert set(r.json().keys()) == {'node_id', 'updated', 'message'}

    def test_mitm_response_schema_shape(self):
        r = self.client.put('/firefox/my-node/mitm-script',
                            json={'content': '# script'})
        assert r.status_code == 200
        assert set(r.json().keys()) == {'node_id', 'uploaded', 'message'}
