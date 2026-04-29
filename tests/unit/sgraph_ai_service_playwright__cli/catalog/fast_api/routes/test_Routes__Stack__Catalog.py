# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — TestClient tests for Routes__Stack__Catalog
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.fast_api.routes.Routes__Stack__Catalog import Routes__Stack__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service
from tests.unit.sgraph_ai_service_playwright__cli.catalog.service.test_Stack__Catalog__Service import (
    _Fake_Linux__Service, _Fake_Docker__Service, _Fake_Elastic__Service)


def _client():
    svc = Stack__Catalog__Service()
    svc.linux_service   = _Fake_Linux__Service()
    svc.docker_service  = _Fake_Docker__Service()
    svc.elastic_service = _Fake_Elastic__Service()
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Stack__Catalog, service=svc)
    return app.client()


class test_Routes__Stack__Catalog(TestCase):

    def test_types__returns_5_entries(self):
        resp = _client().get('/catalog/types')
        assert resp.status_code           == 200
        assert len(resp.json()['entries']) == 5

    def test_types__available_flags(self):
        entries = {e['type_id']: e['available'] for e in _client().get('/catalog/types').json()['entries']}
        assert entries['linux']  is True
        assert entries['docker'] is True
        assert entries['vnc']    is False

    def test_stacks__unfiltered(self):
        resp = _client().get('/catalog/stacks')
        assert resp.status_code == 200
        assert 'stacks' in resp.json()

    def test_stacks__filtered_linux(self):
        resp = _client().get('/catalog/stacks?type=linux')
        assert resp.status_code == 200
        for s in resp.json()['stacks']:
            assert s['type_id'] == 'linux'

    def test_stacks__unknown_type_422(self):
        resp = _client().get('/catalog/stacks?type=banana')
        assert resp.status_code == 422
