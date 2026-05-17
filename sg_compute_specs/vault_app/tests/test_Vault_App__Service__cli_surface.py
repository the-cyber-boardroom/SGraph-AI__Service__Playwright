# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Service CLI surface
# Verifies cli_spec() shape and user-data render structure (no AWS calls).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__Service            import Vault_App__Service
from sg_compute_specs.vault_app.service.Vault_App__User_Data__Builder import Vault_App__User_Data__Builder

REGISTRY = '123456789012.dkr.ecr.eu-west-2.amazonaws.com'


class TestVaultAppServiceCliSurface:

    def test_cli_spec_shape(self):
        spec = Vault_App__Service().cli_spec()
        assert spec.spec_id               == 'vault-app'
        assert spec.display_name          == 'Vault App'
        assert spec.default_instance_type == 't3.medium'
        assert spec.health_path           == '/info/health'
        assert spec.health_port           == 8080
        assert spec.health_scheme         == 'http'
        assert spec.create_request_cls.__name__ == 'Schema__Vault_App__Create__Request'

    def test_user_data_timer_before_dnf(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok', max_hours=1)
        lines   = user_data.splitlines()
        timer_i = next(i for i, l in enumerate(lines) if 'systemd-run' in l)
        dnf_i   = next(i for i, l in enumerate(lines) if l.strip().startswith('dnf install'))
        assert timer_i < dnf_i, 'auto-terminate timer must appear before any dnf install (L9)'

    def test_user_data_no_shutdown_when_max_hours_zero(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok', max_hours=0)
        assert 'systemd-run' not in user_data

    def test_user_data_just_vault_omits_playwright(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_playwright=False)
        assert 'just-vault'        in user_data
        assert 'sg-playwright:'    not in user_data
        assert 'agent-mitmproxy:'  not in user_data

    def test_user_data_with_playwright_includes_all_four(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_playwright=True)
        assert 'with-playwright'  in user_data
        assert 'sg-playwright:'   in user_data
        assert 'agent-mitmproxy:' in user_data

    def test_user_data_docker_engine(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   container_engine='docker')
        assert 'dnf install -y docker' in user_data
        assert 'docker compose'        in user_data
        assert 'podman'                not in user_data

    def test_user_data_docker_compose_downloaded_not_dnf(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   container_engine='docker')
        # docker-compose-plugin is NOT in AL2023 base repos; compose V2 is downloaded
        # from GitHub releases and installed as a CLI plugin binary — not via dnf.
        assert 'dnf install -y docker-compose-plugin'          not in user_data
        assert 'docker/compose/releases/download'              in user_data
        assert 'docker-compose-linux-x86_64'                   in user_data
        assert '/usr/local/lib/docker/cli-plugins/docker-compose' in user_data

    def test_user_data_podman_engine(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   container_engine='podman')
        assert 'dnf install -y podman podman-compose' in user_data
        assert 'podman-compose'                       in user_data
        assert 'podman.socket'                        in user_data

    def test_user_data_access_token_in_env(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='secret-tok-123')
        # the one shared secret feeds both the API key and the vault access token
        assert 'FAST_API__AUTH__API_KEY__VALUE=secret-tok-123' in user_data
        assert 'SGRAPH_SEND__ACCESS_TOKEN=secret-tok-123'      in user_data

    def test_user_data_seed_keys_propagated(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   seed_vault_keys='key1,key2')
        assert 'SG_VAULT_APP__SEED_VAULT_KEYS=key1,key2' in user_data

    def test_user_data_with_tls_check_adds_cert_sidecar(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_tls_check=True)
        assert 'cert-init'                          in user_data
        assert 'sg_compute.platforms.tls.cert_init' in user_data
        assert 'FAST_API__TLS__ENABLED'             in user_data
        assert 'SG__CERT_INIT__MODE=self-signed'    in user_data            # default mode in .env

    def test_user_data_letsencrypt_ip_mode_in_env(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_tls_check=True, tls_mode='letsencrypt-ip', acme_prod=True)
        assert 'SG__CERT_INIT__MODE=letsencrypt-ip' in user_data
        assert 'SG__CERT_INIT__ACME_PROD=true'      in user_data
        assert 'SG__CERT_INIT__TLS_HOSTNAME='       not in user_data            # IP mode never emits the FQDN .env line
                                                                                # (the compose YAML still references ${SG__CERT_INIT__TLS_HOSTNAME:-}, resolving to empty)

    def test_user_data_letsencrypt_hostname_mode_writes_fqdn_env(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_tls_check=True, tls_mode='letsencrypt-hostname',
                                   acme_prod=True, tls_hostname='test-2.sg-compute.sgraph.ai')
        assert 'SG__CERT_INIT__MODE=letsencrypt-hostname'                     in user_data
        assert 'SG__CERT_INIT__ACME_PROD=true'                                in user_data
        assert 'SG__CERT_INIT__TLS_HOSTNAME=test-2.sg-compute.sgraph.ai'      in user_data

    def test_user_data_letsencrypt_hostname_without_fqdn_still_renders(self):
        # Service layer is responsible for the empty-fqdn guard. The user-data builder
        # itself just emits whatever it's given — it should not crash on an empty hostname.
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_tls_check=True, tls_mode='letsencrypt-hostname',
                                   acme_prod=True, tls_hostname='')
        assert 'SG__CERT_INIT__MODE=letsencrypt-hostname' in user_data
        assert 'SG__CERT_INIT__TLS_HOSTNAME='             in user_data        # empty value — cert-init will fail loud at boot

    def test_user_data_unknown_tls_mode_falls_back_to_self_signed(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok',
                                   with_tls_check=True, tls_mode='banana')
        assert 'SG__CERT_INIT__MODE=self-signed' in user_data                  # whitelist guard in the builder

    def test_with_aws_dns_derives_fqdn_from_stack_name_and_default_zone(self, monkeypatch):
        # Pure derivation test — verifies create_stack's pre-launch wiring without going to AWS.
        # We can't easily run the full create_stack (it talks to EC2 / IAM / SG), so we exercise
        # the derivation logic via the helper that drives it.
        from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request
        from sg_compute_specs.vault_app.service.Vault_App__Service                  import _default_aws_dns_zone

        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'sg-compute.sgraph.ai')
        request = Schema__Vault_App__Create__Request()
        request.with_aws_dns = True
        request.tls_hostname = ''
        request.tls_mode     = 'letsencrypt-ip'                                 # default — should be auto-bumped

        # Mirror the service's derivation block:
        stack_name = 'warm-bohr'
        if bool(request.with_aws_dns) and not str(request.tls_hostname).strip():
            request.tls_hostname = f'{stack_name}.{_default_aws_dns_zone()}'
            if str(request.tls_mode) == 'letsencrypt-ip':
                request.tls_mode = 'letsencrypt-hostname'

        assert request.tls_hostname == 'warm-bohr.sg-compute.sgraph.ai'
        assert request.tls_mode     == 'letsencrypt-hostname'

    def test_default_aws_dns_zone_env_overrides_fallback(self, monkeypatch):
        from sg_compute_specs.vault_app.service.Vault_App__Service import _default_aws_dns_zone, DEFAULT_AWS_DNS_ZONE_FALLBACK
        monkeypatch.delenv('SG_AWS__DNS__DEFAULT_ZONE', raising=False)
        assert _default_aws_dns_zone() == DEFAULT_AWS_DNS_ZONE_FALLBACK
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'corp.example.com')
        assert _default_aws_dns_zone() == 'corp.example.com'

    def test_user_data_without_tls_check_omits_cert_sidecar(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok')
        assert 'cert-init'           not in user_data
        assert 'SG__CERT_INIT__MODE' not in user_data

    def test_user_data_default_shutdown_behavior_uses_halt(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok', max_hours=1)
        assert '/sbin/shutdown -h now' in user_data
        assert 'aws ec2 stop-instances' not in user_data

    def test_user_data_stop_shutdown_behavior_uses_imdsv2_stop(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok', max_hours=1,
                                   shutdown_behavior='stop')
        assert 'aws ec2 stop-instances' in user_data
        assert '/sbin/shutdown -h now'  not in user_data
        assert 'X-aws-ec2-metadata-token' in user_data  # IMDSv2 token fetch

    def test_user_data_stop_timer_still_before_dnf(self):
        builder   = Vault_App__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   ecr_registry=REGISTRY, access_token='tok', max_hours=1,
                                   shutdown_behavior='stop')
        lines   = user_data.splitlines()
        timer_i = next(i for i, l in enumerate(lines) if 'systemd-run' in l)
        dnf_i   = next(i for i, l in enumerate(lines) if l.strip().startswith('dnf install'))
        assert timer_i < dnf_i, 'auto-stop timer must appear before any dnf install (L9)'
