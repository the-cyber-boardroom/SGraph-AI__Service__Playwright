# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Stack__Catalog__Service
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service
from tests.unit.sgraph_ai_service_playwright__cli.catalog.service.test_Stack__Catalog__Service import (
    _Fake_Linux__Service, _Fake_Docker__Service, _Fake_Elastic__Service)


def _svc():
    svc = Stack__Catalog__Service()
    svc.linux_service   = _Fake_Linux__Service()
    svc.docker_service  = _Fake_Docker__Service()
    svc.elastic_service = _Fake_Elastic__Service()
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
        assert entries[Enum__Stack__Type.VNC]        is False

    def test_list_all_stacks__unfiltered(self):
        result = _svc().list_all_stacks()
        types  = {s.type_id for s in result.stacks}
        assert Enum__Stack__Type.LINUX  in types
        assert Enum__Stack__Type.DOCKER in types
        assert len(result.stacks) == 2                                              # 1 linux + 1 docker; elastic fake returns empty

    def test_list_all_stacks__filtered_linux(self):
        result = _svc().list_all_stacks(type_filter=Enum__Stack__Type.LINUX)
        assert all(s.type_id == Enum__Stack__Type.LINUX for s in result.stacks)
        assert len(result.stacks) == 1

    def test_list_all_stacks__filtered_docker(self):
        result = _svc().list_all_stacks(type_filter=Enum__Stack__Type.DOCKER)
        assert all(s.type_id == Enum__Stack__Type.DOCKER for s in result.stacks)
        assert len(result.stacks) == 1
