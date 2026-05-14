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
