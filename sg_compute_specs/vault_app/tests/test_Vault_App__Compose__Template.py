# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Compose__Template
# Verifies the 2-vs-4 container shapes and the single published port.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__Compose__Template import (Vault_App__Compose__Template,
                                                                              SG_SEND_VAULT_IMAGE        )

REGISTRY = '123456789012.dkr.ecr.eu-west-2.amazonaws.com'


class TestVaultAppComposeTemplate:

    def test_just_vault_has_two_services(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=False)
        assert 'host-plane:'      in result
        assert 'sg-send-vault:'   in result
        assert 'sg-playwright:'   not in result
        assert 'agent-mitmproxy:' not in result

    def test_with_playwright_has_four_services(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=True)
        assert 'host-plane:'      in result
        assert 'sg-send-vault:'   in result
        assert 'sg-playwright:'   in result
        assert 'agent-mitmproxy:' in result

    def test_only_vault_port_published(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=True)
        assert '"8080:8080"' in result
        assert '8000:8000'   not in result          # playwright never published
        assert '8081:'       not in result          # mitmproxy never published

    def test_sg_send_vault_default_image(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY)
        assert SG_SEND_VAULT_IMAGE in result

    def test_vault_net_network_defined(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY)
        assert 'vault-net'      in result
        assert 'driver: bridge' in result

    def test_ecr_registry_interpolated(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY)
        assert f'{REGISTRY}/sgraph_ai_service_playwright_host' in result

    def test_podman_socket_path(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY,
                                                       docker_socket='/run/podman/podman.sock')
        assert '/run/podman/podman.sock:/var/run/docker.sock' in result
