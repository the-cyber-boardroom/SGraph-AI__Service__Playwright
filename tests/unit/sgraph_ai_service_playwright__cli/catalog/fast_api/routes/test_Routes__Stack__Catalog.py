# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — TestClient tests for Routes__Stack__Catalog
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.fast_api.routes.Routes__Stack__Catalog import Routes__Stack__Catalog
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service
from tests.unit.sgraph_ai_service_playwright__cli.catalog.service.test_Stack__Catalog__Service import _fake_registry


def _client():
    svc = Stack__Catalog__Service()
    svc.plugin_registry = _fake_registry()
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
        assert entries['docker']     is True
        assert entries['podman']     is True
        assert entries['opensearch'] is False
        assert entries['vnc']        is True

    def test_stacks__returns_200_with_stacks_key(self):
        resp = _client().get('/catalog/stacks')
        assert resp.status_code == 200
        assert 'stacks' in resp.json()

    def test_stacks__contains_enabled_plugin_stacks(self):
        resp   = _client().get('/catalog/stacks')
        types  = {s['type_id'] for s in resp.json()['stacks']}
        assert 'podman' in types
        assert 'docker' in types
        assert 'vnc'    in types
