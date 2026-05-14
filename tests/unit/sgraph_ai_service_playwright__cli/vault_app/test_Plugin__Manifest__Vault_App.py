# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Plugin__Manifest__Vault_App
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.vault_app.fast_api.routes.Routes__Vault_App__Stack \
                                                                                    import Routes__Vault_App__Stack
from sgraph_ai_service_playwright__cli.vault_app.plugin.Plugin__Manifest__Vault_App import Plugin__Manifest__Vault_App
from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Service         import Vault_App__Service


class test_Plugin__Manifest__Vault_App(TestCase):

    def setUp(self):
        self.manifest = Plugin__Manifest__Vault_App()

    def test__name_and_display(self):
        assert str(self.manifest.name) == 'vault_app'
        assert self.manifest.display_name == 'Vault App'
        assert self.manifest.enabled is True
        assert self.manifest.stability == Enum__Plugin__Stability.EXPERIMENTAL

    def test__capabilities(self):
        caps = list(self.manifest.capabilities)
        assert Enum__Plugin__Capability.VAULT_WRITES   in caps
        assert Enum__Plugin__Capability.MITM_PROXY     in caps
        assert Enum__Plugin__Capability.REMOTE_SHELL   in caps
        assert Enum__Plugin__Capability.SIDECAR_ATTACH in caps

    def test__service_class(self):
        assert self.manifest.service_class() is Vault_App__Service

    def test__routes_classes(self):
        assert self.manifest.routes_classes() == [Routes__Vault_App__Stack]

    def test__catalog_entry(self):
        entry = self.manifest.catalog_entry()
        assert entry.type_id              == Enum__Stack__Type.VAULT_APP
        assert str(entry.create_endpoint_path) == '/vault-app/stack'
        assert str(entry.list_endpoint_path)   == '/vault-app/stacks'
        assert str(entry.health_endpoint_path) == '/vault-app/stack/{name}/health'
        assert entry.available is True

    def test__event_topics_emitted(self):
        topics = self.manifest.event_topics_emitted()
        assert 'vault_app:stack.created' in topics
        assert 'vault_app:stack.deleted' in topics
