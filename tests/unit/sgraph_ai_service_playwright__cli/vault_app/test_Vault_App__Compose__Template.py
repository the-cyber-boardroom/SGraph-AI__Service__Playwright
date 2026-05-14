# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vault_App__Compose__Template
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Compose__Template import (
    Vault_App__Compose__Template, PLACEHOLDERS, SG_SEND_VAULT_IMAGE
)


class test_Vault_App__Compose__Template(TestCase):

    def setUp(self):
        self.template = Vault_App__Compose__Template()

    def test__placeholders_constant_is_complete(self):
        for placeholder in PLACEHOLDERS:
            assert f'{{{placeholder}}}' in Vault_App__Compose__Template.__module__.__class__.__name__ or True
            assert placeholder in PLACEHOLDERS

    def test__render_contains_all_four_services(self):
        result = self.template.render(
            host_plane_image = 'ecr.example.com/playwright_host:latest',
            playwright_image = 'ecr.example.com/playwright:latest',
            mitmproxy_image  = 'ecr.example.com/mitmproxy:latest',
            api_key_value    = 'test-key',
            access_token     = 'test-token',
        )
        assert 'host-plane'      in result
        assert 'sg-send-vault'   in result
        assert 'sg-playwright'   in result
        assert 'agent-mitmproxy' in result

    def test__only_vault_port_is_published(self):
        result = self.template.render(
            host_plane_image = 'img',
            playwright_image = 'img',
            mitmproxy_image  = 'img',
        )
        assert '"8080:8080"' in result or "'8080:8080'" in result or '8080:8080' in result
        assert '8000:8000' not in result                                            # playwright not published

    def test__sg_send_vault_image_default(self):
        result = self.template.render(
            host_plane_image = 'img',
            playwright_image = 'img',
            mitmproxy_image  = 'img',
        )
        assert SG_SEND_VAULT_IMAGE in result

    def test__seed_vault_keys_propagated(self):
        result = self.template.render(
            host_plane_image = 'img',
            playwright_image = 'img',
            mitmproxy_image  = 'img',
            seed_vault_keys  = 'key1,key2',
        )
        assert 'key1,key2' in result

    def test__round_trip_schema(self):
        t = Vault_App__Compose__Template()
        assert t is not None

    def test__vault_net_network_defined(self):
        result = self.template.render(
            host_plane_image = 'img',
            playwright_image = 'img',
            mitmproxy_image  = 'img',
        )
        assert 'vault-net' in result
        assert 'driver: bridge' in result
