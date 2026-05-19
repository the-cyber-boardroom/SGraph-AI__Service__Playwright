# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Compose__Template
# Verifies the 1-vs-4 container shapes and the single published port.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__Compose__Template import (Vault_App__Compose__Template,
                                                                              SG_SEND_VAULT_IMAGE        )


class TestVaultAppComposeTemplate:

    def test_just_vault_has_one_service(self):
        result = Vault_App__Compose__Template().render(with_playwright=False)
        assert 'host-plane:'      not in result
        assert 'sg-send-vault:'   in result
        assert 'sg-playwright:'   not in result
        assert 'agent-mitmproxy:' not in result

    def test_with_playwright_has_four_services(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'host-plane:'      in result
        assert 'sg-send-vault:'   in result
        assert 'sg-playwright:'   in result
        assert 'agent-mitmproxy:' in result

    def test_only_vault_port_published(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert '"8080:8080"' in result
        assert '8000:8000'   not in result          # playwright never published
        assert '8081:'       not in result          # mitmproxy web UI never published

    def test_sg_send_vault_default_image(self):
        result = Vault_App__Compose__Template().render()
        assert SG_SEND_VAULT_IMAGE in result

    def test_vault_net_network_defined(self):
        result = Vault_App__Compose__Template().render()
        assert 'vault-net'      in result
        assert 'driver: bridge' in result

    def test_no_ecr_in_any_shape(self):
        just_vault = Vault_App__Compose__Template().render(with_playwright=False)
        with_pw    = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'ecr'            not in just_vault.lower()
        assert 'ecr'            not in with_pw.lower()
        assert 'docker login'   not in with_pw

    def test_agent_mitmproxy_uses_docker_hub(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'image: mitmproxy/mitmproxy:latest' in result
        assert 'mitmweb'                           in result
        assert 'block_global=false'                in result
        assert '"127.0.0.1:19081:8000"'            not in result             # no admin FastAPI port

    def test_podman_socket_path(self):
        result = Vault_App__Compose__Template().render(with_playwright=True,
                                                       docker_socket='/run/podman/podman.sock')
        assert '/run/podman/podman.sock:/var/run/docker.sock' in result

    def test_with_playwright_publishes_external_port(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert '"80:8000"' in result                                 # host:80 → container:8000

    def test_with_playwright_pulls_docker_hub_image(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'image: diniscruz/sg-playwright:latest' in result

    def test_without_playwright_does_not_publish_playwright_port(self):
        result = Vault_App__Compose__Template().render()
        assert '"80:8000"' not in result                             # only published when --with-playwright

    def test_host_plane_no_longer_carries_dead_mitmweb_env(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'AGENT_MITMPROXY__MITMWEB_HOST' not in result

    def test_host_plane_uses_docker_hub_image(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'image: diniscruz/sg-host-control:latest'       in result
        assert 'sg_compute.host_plane.fast_api.lambda_handler' not in result

    def test_cert_init_uses_docker_hub_image(self):
        result = Vault_App__Compose__Template().render(with_tls_check=True)
        assert 'image: diniscruz/sg-host-control:latest'   in result
        assert 'sg_compute.platforms.tls.cert_init'        in result

    def test_with_tls_check_wires_tls_into_sg_send_vault(self):
        result = Vault_App__Compose__Template().render(with_tls_check=True)
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
        result = Vault_App__Compose__Template().render(with_tls_check=True)
        assert 'SG__CERT_INIT__MODE'         in result                     # self-signed | letsencrypt-ip | letsencrypt-hostname
        assert 'SG__CERT_INIT__ACME_PROD'    in result
        assert 'SG__CERT_INIT__TLS_HOSTNAME' in result                     # plumbing for letsencrypt-hostname mode
        assert '"80:80"'                     in result                     # http-01 challenge listener

    def test_without_tls_check_omits_cert_services(self):
        result = Vault_App__Compose__Template().render()
        assert 'cert-init'              not in result
        assert 'FAST_API__TLS__ENABLED' not in result
        assert '\nvolumes:\n'           not in result                      # service-level `    volumes:` still allowed
        assert '"8080:8080"'            in result                          # plain stack keeps the HTTP port
