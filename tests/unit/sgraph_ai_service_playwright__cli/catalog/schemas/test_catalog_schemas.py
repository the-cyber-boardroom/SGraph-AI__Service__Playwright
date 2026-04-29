# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for catalog schemas
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Summary       import Schema__Stack__Summary


class test_Schema__Stack__Type__Catalog__Entry(TestCase):

    def test_defaults(self):
        entry = Schema__Stack__Type__Catalog__Entry()
        assert entry.available             is False
        assert entry.default_max_hours     == 4
        assert entry.expected_boot_seconds == 60

    def test_json_round_trip(self):
        entry = Schema__Stack__Type__Catalog__Entry(
            type_id=Enum__Stack__Type.LINUX, display_name='Bare Linux',
            available=True, expected_boot_seconds=60)
        data = entry.json()
        assert data['type_id']               == 'linux'
        assert data['available']             is True
        assert data['expected_boot_seconds'] == 60


class test_Schema__Stack__Summary(TestCase):

    def test_defaults(self):
        s = Schema__Stack__Summary()
        assert s.uptime_seconds == 0

    def test_json_round_trip(self):
        s = Schema__Stack__Summary(
            type_id=Enum__Stack__Type.DOCKER, stack_name='docker-test',
            state='running', uptime_seconds=42)
        data = s.json()
        assert data['type_id']        == 'docker'
        assert data['stack_name']     == 'docker-test'
        assert data['uptime_seconds'] == 42
