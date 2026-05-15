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

    def test_with_playwright_publishes_external_port(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=True)
        assert '"11024:8000"' in result                              # host:11024 → container:8000

    def test_with_playwright_pulls_docker_hub_image(self):
        # sg-playwright follows the sg-send-vault pattern: a Docker Hub image, not ECR.
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=True)
        assert 'image: diniscruz/sg-playwright:latest'                    in result
        assert f'{REGISTRY}/sgraph_ai_service_playwright:' + 'latest'     not in result

    def test_without_playwright_does_not_publish_11024(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY)
        assert '11024' not in result

    def test_with_playwright_publishes_mitmweb_admin_on_localhost(self):
        # Routes__Web lives on agent-mitmproxy's admin FastAPI (:8000), NOT on
        # host-plane. Publishing it as 127.0.0.1:19081 gives SSM port-forward a
        # target so /web/ is reachable from a laptop.
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=True)
        assert '"127.0.0.1:19081:8000"' in result

    def test_host_plane_no_longer_carries_dead_mitmweb_env(self):
        # An earlier commit added AGENT_MITMPROXY__MITMWEB_HOST to host-plane based
        # on the wrong assumption that Routes__Web ran there. It doesn't.
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_playwright=True)
        assert 'AGENT_MITMPROXY__MITMWEB_HOST' not in result

    def test_with_tls_check_wires_tls_into_sg_send_vault(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_tls_check=True)
        # the real sg-send-vault service terminates its own HTTPS — no proxy, no scaffold
        assert 'cert-init:'                             in result
        assert 'sg_compute.platforms.tls.cert_init'     in result
        assert 'tls-check:'                             not in result      # P0 scaffold dropped
        assert 'FAST_API__TLS__ENABLED:        "true"'  in result
        assert 'certs:/certs:ro'                        in result
        assert '"443:443"'                              in result
        assert '"8080:8080"'                            not in result      # TLS on → :443 only
        assert 'service_completed_successfully'         in result
        assert '\nvolumes:\n'                           in result          # top-level volumes block
        assert 'certs:'                                 in result

    def test_with_tls_check_cert_init_exposes_acme_challenge_port(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY, with_tls_check=True)
        assert 'SG__CERT_INIT__MODE'      in result                        # self-signed | letsencrypt-ip
        assert 'SG__CERT_INIT__ACME_PROD' in result
        assert '"80:80"'                  in result                        # http-01 challenge listener

    def test_without_tls_check_omits_cert_services(self):
        result = Vault_App__Compose__Template().render(ecr_registry=REGISTRY)
        assert 'cert-init'              not in result
        assert 'FAST_API__TLS__ENABLED' not in result
        assert '\nvolumes:\n'           not in result                      # service-level `    volumes:` still allowed
        assert '"8080:8080"'            in result                          # plain stack keeps the HTTP port
