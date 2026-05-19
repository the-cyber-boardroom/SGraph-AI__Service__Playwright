# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Spec
# Covers: env_for_run contract, port_mappings shape, default constant values.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Spec import Vault_App__Fargate__Spec


class test_Vault_App__Fargate__Spec(TestCase):

    def setUp(self):
        self.spec = Vault_App__Fargate__Spec()

    # ── default constants ────────────────────────────────────────────────────

    def test_default_image_repo_name(self):
        assert self.spec.image_repo_name == 'sg-send-vault'

    def test_default_image_tag(self):
        assert self.spec.image_tag == 'latest'

    def test_default_container_name(self):
        assert self.spec.container_name == 'vault'

    def test_default_health_path(self):
        assert self.spec.health_path == '/info/health'

    def test_default_http_port(self):
        assert self.spec.http_port == 8080

    def test_default_https_port(self):
        assert self.spec.https_port == 443

    def test_default_acme_port(self):
        assert self.spec.acme_port == 80

    def test_default_cpu(self):
        assert self.spec.default_cpu == '512'

    def test_default_memory(self):
        assert self.spec.default_memory == '1024'

    def test_default_log_group(self):
        assert self.spec.default_log_group == '/ecs/vault-app'

    def test_default_cluster(self):
        assert self.spec.default_cluster == 'vault-app'

    def test_default_task_def_family(self):
        assert self.spec.default_task_def_family == 'vault-app'

    # ── env_for_run ──────────────────────────────────────────────────────────

    def test_env_for_run_storage_mode_always_memory(self):
        env = self.spec.env_for_run(access_token='tok')
        assert env['SEND__STORAGE_MODE'] == 'memory'

    def test_env_for_run_includes_access_token(self):
        env = self.spec.env_for_run(access_token='sg_abc123')
        assert env['SEND__ACCESS_TOKEN'] == 'sg_abc123'

    def test_env_for_run_tls_enabled_by_default(self):
        env = self.spec.env_for_run(access_token='tok')
        assert env.get('SEND__TLS_ENABLED') == 'true'

    def test_env_for_run_tls_absent_when_false(self):
        env = self.spec.env_for_run(access_token='tok', with_tls=False)
        assert 'SEND__TLS_ENABLED' not in env

    def test_env_for_run_seed_vault_keys_present_when_given(self):
        env = self.spec.env_for_run(access_token='tok', seed_vault_keys='key1,key2')
        assert env['SEND__SEED_VAULT_KEYS'] == 'key1,key2'

    def test_env_for_run_seed_vault_keys_absent_when_empty(self):
        env = self.spec.env_for_run(access_token='tok', seed_vault_keys='')
        assert 'SEND__SEED_VAULT_KEYS' not in env

    def test_env_for_run_returns_dict(self):
        env = self.spec.env_for_run(access_token='tok')
        assert isinstance(env, dict)

    def test_env_for_run_storage_mode_not_overridable(self):
        # SEND__STORAGE_MODE is always 'memory' — no parameter for it (Q1/Q6)
        env = self.spec.env_for_run(access_token='tok')
        assert env['SEND__STORAGE_MODE'] == 'memory'

    # ── port_mappings ────────────────────────────────────────────────────────

    def test_port_mappings_returns_list(self):
        pm = self.spec.port_mappings()
        assert isinstance(pm, list)

    def test_port_mappings_has_three_entries(self):
        pm = self.spec.port_mappings()
        assert len(pm) == 3

    def test_port_mappings_contains_http_port(self):
        ports = {p['containerPort'] for p in self.spec.port_mappings()}
        assert 8080 in ports

    def test_port_mappings_contains_https_port(self):
        ports = {p['containerPort'] for p in self.spec.port_mappings()}
        assert 443 in ports

    def test_port_mappings_contains_acme_port(self):
        ports = {p['containerPort'] for p in self.spec.port_mappings()}
        assert 80 in ports

    def test_port_mappings_all_tcp_protocol(self):
        for pm in self.spec.port_mappings():
            assert pm['protocol'] == 'tcp'
