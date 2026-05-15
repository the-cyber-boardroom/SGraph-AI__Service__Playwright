# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Plugin__Manifest__Playwright
# Manifest properties, catalog entry, routes + service wiring.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type               import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability    import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group     import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability     import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.playwright.fast_api.routes.Routes__Playwright__Stack import Routes__Playwright__Stack
from sgraph_ai_service_playwright__cli.playwright.plugin.Plugin__Manifest__Playwright import Plugin__Manifest__Playwright
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Service  import Playwright__Stack__Service


class test_Plugin__Manifest__Playwright(TestCase):

    def setUp(self):
        self.manifest = Plugin__Manifest__Playwright()

    def test__properties(self):
        assert str(self.manifest.name)  == 'playwright'
        assert str(self.manifest.icon)  == '🎭'
        assert self.manifest.enabled    is True
        assert self.manifest.stability  == Enum__Plugin__Stability.EXPERIMENTAL
        assert self.manifest.nav_group  == Enum__Plugin__Nav_Group.COMPUTE

    def test__service_class(self):
        assert self.manifest.service_class() is Playwright__Stack__Service

    def test__routes_classes(self):
        assert self.manifest.routes_classes() == [Routes__Playwright__Stack]

    def test__capabilities(self):
        caps = list(self.manifest.capabilities)
        assert Enum__Plugin__Capability.MITM_PROXY   in caps
        assert Enum__Plugin__Capability.VAULT_WRITES in caps

    def test__catalog_entry(self):
        entry = self.manifest.catalog_entry()
        assert entry.type_id                    == Enum__Stack__Type.PLAYWRIGHT
        assert entry.available                  is True
        assert str(entry.create_endpoint_path)  == '/playwright/stack'
        assert str(entry.list_endpoint_path)    == '/playwright/stacks'
        assert str(entry.info_endpoint_path)    == '/playwright/stack/{name}'
        assert str(entry.delete_endpoint_path)  == '/playwright/stack/{name}'
        assert str(entry.health_endpoint_path)  == '/playwright/stack/{name}/health'

    def test__event_topics_emitted(self):
        topics = self.manifest.event_topics_emitted()
        assert 'playwright:stack.created' in topics
        assert 'playwright:stack.deleted' in topics

    def test__manifest_entry__shape(self):
        from sgraph_ai_service_playwright__cli.core.plugin.schemas.Schema__Plugin__Manifest__Entry import Schema__Plugin__Manifest__Entry
        entry = self.manifest.manifest_entry()
        assert isinstance(entry, Schema__Plugin__Manifest__Entry)
        assert str(entry.icon)                 == '🎭'
        assert str(entry.create_endpoint_path) == '/playwright/stack'
