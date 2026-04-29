# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Stack__Catalog__Service
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service
from tests.unit.sgraph_ai_service_playwright__cli.catalog.service.test_Stack__Catalog__Service import _fake_registry


def _svc():
    svc = Stack__Catalog__Service()
    svc.plugin_registry = _fake_registry()
    return svc


class test_Stack__Catalog__Service__catalog(TestCase):

    def test_get_catalog__returns_5_entries(self):
        catalog = _svc().get_catalog()
        assert len(catalog.entries) == 5

    def test_get_catalog__available_flags(self):
        entries = {e.type_id: e.available for e in _svc().get_catalog().entries}
        assert entries[Enum__Stack__Type.LINUX]      is True
        assert entries[Enum__Stack__Type.DOCKER]     is True
        assert entries[Enum__Stack__Type.ELASTIC]    is True
        assert entries[Enum__Stack__Type.OPENSEARCH] is False
        assert entries[Enum__Stack__Type.VNC]        is True

    def test_list_all_stacks__returns_enabled_plugin_stacks(self):
        result = _svc().list_all_stacks()
        types  = {s.type_id for s in result.stacks}
        assert Enum__Stack__Type.LINUX  in types
        assert Enum__Stack__Type.DOCKER in types
        assert Enum__Stack__Type.VNC    in types
        assert len(result.stacks) == 3                                              # 1 linux + 1 docker + 1 vnc; elastic fake returns empty
