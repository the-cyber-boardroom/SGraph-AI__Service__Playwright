# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__AMI__Helper
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__AMI__Helper import (AL2023_SSM_PARAM        ,
                                                                        Vault_App__AMI__Helper )


class TestVaultAppAMIHelper:

    def test_ssm_param_constant(self):
        assert 'al2023' in AL2023_SSM_PARAM.lower()

    def test_resolve_uses_from_ami_when_given(self):
        helper = Vault_App__AMI__Helper()
        # from_ami short-circuits — no AWS call
        assert helper.resolve('eu-west-2', from_ami='ami-explicit') == 'ami-explicit'

    def test_resolve_falls_back_to_latest_al2023(self, monkeypatch):
        helper = Vault_App__AMI__Helper()
        monkeypatch.setattr(helper, 'latest_al2023', lambda region: f'ami-al2023-{region}')
        assert helper.resolve('eu-west-2') == 'ami-al2023-eu-west-2'
