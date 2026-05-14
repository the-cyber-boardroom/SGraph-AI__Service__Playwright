# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__Vault_App__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request


class TestSchemaVaultAppCreateRequest:

    def test_defaults(self):
        req = Schema__Vault_App__Create__Request()
        assert req.region            == 'eu-west-2'
        assert req.instance_type     == 't3.medium'
        assert req.from_ami          == ''
        assert req.stack_name        == ''
        assert req.caller_ip         == ''
        assert req.max_hours         == 1.0
        assert req.with_playwright   is False           # default = just-vault (2 containers)
        assert req.container_engine  == 'docker'
        assert req.storage_mode      == 'disk'
        assert req.seed_vault_keys   == ''
        assert req.access_token      == ''
        assert req.disk_size_gb      == 20
        assert req.use_spot          is True

    def test_override_with_playwright(self):
        req = Schema__Vault_App__Create__Request()
        req.with_playwright = True
        assert req.with_playwright is True

    def test_override_container_engine(self):
        req = Schema__Vault_App__Create__Request()
        req.container_engine = 'podman'
        assert req.container_engine == 'podman'

    def test_override_use_spot_false(self):
        req = Schema__Vault_App__Create__Request()
        req.use_spot = False
        assert req.use_spot is False
