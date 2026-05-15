# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cert__ACME__Client
# Covers the offline, deterministic surface: staging/prod directory selection,
# cert-key generation, and the IP-SAN CSR builder. The actual ACME network
# exchange with Let's Encrypt is not unit-testable (no public IP, real CA, rate
# limits) — it is verified by a live deploy run.
#
# build_csr needs the `acme` library; it is importorskip-guarded so the file
# still runs on the project's py3.11 env where `acme` is not installed.
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress

import pytest

from sg_compute.platforms.tls.Cert__ACME__Client import (Cert__ACME__Client     ,
                                                          LE_DIRECTORY__STAGING ,
                                                          LE_DIRECTORY__PROD    )


class TestCertACMEClient:

    def test_config_defaults_to_staging(self):
        config = Cert__ACME__Client().config()
        assert config.directory_url == LE_DIRECTORY__STAGING
        assert 'staging' in config.directory_url
        assert config.profile        == 'shortlived'        # LE requires this for IP certs
        assert config.challenge_port == 80

    def test_config_prod_opt_in(self):
        config = Cert__ACME__Client().config(prod=True, contact_email='ops@example.com')
        assert config.directory_url == LE_DIRECTORY__PROD
        assert 'staging' not in config.directory_url
        assert config.contact_email == 'ops@example.com'

    def test_build_cert_key_pem_is_a_private_key(self):
        pem = Cert__ACME__Client().build_cert_key_pem()
        assert b'BEGIN PRIVATE KEY' in pem

    def test_build_csr_carries_the_ip_as_san(self):
        pytest.importorskip('acme')
        from cryptography import x509

        client = Cert__ACME__Client()
        csr    = client.build_csr(client.build_cert_key_pem(), '13.40.119.90')
        req    = x509.load_pem_x509_csr(csr)
        san    = req.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        assert ipaddress.ip_address('13.40.119.90') in san.get_values_for_type(x509.IPAddress)

    def test_build_csr_with_hostname_carries_the_dns_name_as_san(self):
        pytest.importorskip('acme')
        from cryptography import x509

        client = Cert__ACME__Client()
        csr    = client.build_csr(client.build_cert_key_pem(), hostname='test-2.sg-compute.sgraph.ai')
        req    = x509.load_pem_x509_csr(csr)
        san    = req.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        assert 'test-2.sg-compute.sgraph.ai' in san.get_values_for_type(x509.DNSName)
        assert san.get_values_for_type(x509.IPAddress) == []                                          # no IP SAN — DNS-only cert

    def test_build_csr_requires_exactly_one_of_ip_or_hostname(self):
        pytest.importorskip('acme')
        client = Cert__ACME__Client()
        key    = client.build_cert_key_pem()

        with pytest.raises(ValueError, match='exactly one of ip / hostname'):    # neither
            client.build_csr(key)
        with pytest.raises(ValueError, match='exactly one of ip / hostname'):    # both
            client.build_csr(key, '1.2.3.4', hostname='example.com')

    def test_config_for_hostname_clears_the_shortlived_profile(self):
        config = Cert__ACME__Client().config(for_hostname=True)
        assert config.profile == ''                                              # DNS-name certs use the LE default profile
        assert config.challenge_port == 80                                       # http-01 port unchanged

    def test_issue_rejects_neither_or_both_id_inputs(self):
        pytest.importorskip('acme')                                              # network not exercised — fails fast on validation before any LE call
        client = Cert__ACME__Client()
        with pytest.raises(ValueError, match='exactly one of ip / hostname'):
            client.issue(cert_path='/tmp/c.pem', key_path='/tmp/k.pem')
        with pytest.raises(ValueError, match='exactly one of ip / hostname'):
            client.issue(ip='1.2.3.4', hostname='example.com', cert_path='/tmp/c.pem', key_path='/tmp/k.pem')
