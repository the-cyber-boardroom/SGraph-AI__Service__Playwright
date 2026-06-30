# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Service._preflight_aws_dns_zone
# --with-aws-dns must fail fast (before launching the EC2) when this account hosts
# no Route 53 zone for the FQDN — otherwise the upsert fails silently, the FQDN
# never resolves, and cert-init times out 180s later (10-minute boot failure).
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.vault_app.service.Vault_App__Service import Vault_App__Service


class _Resolver__Found:
    def __init__(self, fqdn): self.fqdn = fqdn
    def resolve_zone_for_fqdn(self, fqdn):
        assert fqdn == self.fqdn
        return {'zone_id': 'Z123', 'name': 'sg-compute.sgraph.ai'}


class _Resolver__Missing:
    def resolve_zone_for_fqdn(self, fqdn):
        raise ValueError(f"No hosted zone in account owns '{fqdn}'")


class TestPreflightAwsDnsZone:

    def test_passes_when_zone_owned(self):
        svc = Vault_App__Service()
        svc._aws_dns_zone_resolver_factory = lambda: _Resolver__Found('kind-planck.sg-compute.sgraph.ai')
        # no raise
        svc._preflight_aws_dns_zone('kind-planck.sg-compute.sgraph.ai')

    def test_raises_actionable_error_when_zone_not_in_account(self):
        svc = Vault_App__Service()
        svc._aws_dns_zone_resolver_factory = lambda: _Resolver__Missing()
        with pytest.raises(ValueError) as ei:
            svc._preflight_aws_dns_zone('kind-planck.sg-compute.sgraph.ai')
        msg = str(ei.value)
        assert '--with-aws-dns'    in msg
        assert 'hosted zone'       in msg
        assert '--no-with-aws-dns' in msg                   # points at the escape hatch
        assert 'kind-planck.sg-compute.sgraph.ai' in msg    # names the FQDN

    def test_wraps_any_resolver_failure(self):
        # e.g. missing AWS creds — still a fail-fast, not a 10-min boot failure
        class _Boom:
            def resolve_zone_for_fqdn(self, fqdn): raise RuntimeError('NoCredentialsError')
        svc = Vault_App__Service()
        svc._aws_dns_zone_resolver_factory = lambda: _Boom()
        with pytest.raises(ValueError, match='NoCredentialsError'):
            svc._preflight_aws_dns_zone('x.sg-compute.sgraph.ai')
