# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cert__Inspector
# Decoding a cert from PEM bytes/str and from a file, round-tripped against
# Cert__Generator. inspect_host is not exercised here (needs a live TLS server)
# but shares the inspect_pem path that is.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.platforms.tls.Cert__Generator    import Cert__Generator
from sg_compute.platforms.tls.Cert__Inspector    import Cert__Inspector
from sg_compute.platforms.tls.Schema__Cert__Info import Schema__Cert__Info


class TestCertInspector:

    def test_inspect_pem_roundtrip(self):
        material = Cert__Generator().generate('1.2.3.4', sans=['vault.local'], days_valid=160)
        info     = Cert__Inspector().inspect_pem(material.cert_pem, source='test')
        assert type(info) is Schema__Cert__Info
        assert info.is_self_signed is True
        assert info.is_expired     is False
        assert 157 <= info.days_remaining <= 160
        assert 'CN=1.2.3.4'  in info.subject
        assert '1.2.3.4'     in info.sans
        assert 'vault.local' in info.sans
        assert info.fingerprint_sha256.count(':') == 31                # sha256 = 32 bytes
        assert info.source == 'test'

    def test_inspect_pem_accepts_bytes(self):
        material = Cert__Generator().generate('x.local')
        info     = Cert__Inspector().inspect_pem(material.cert_pem.encode())
        assert info.is_self_signed is True

    def test_inspect_file(self, tmp_path):
        cert_path = str(tmp_path / 'cert.pem')
        key_path  = str(tmp_path / 'key.pem')
        Cert__Generator().generate_to_files(cert_path, key_path, 'host.local')
        info = Cert__Inspector().inspect_file(cert_path)
        assert info.source == f'file:{cert_path}'
        assert 'CN=host.local' in info.subject

    def test_short_lived_cert_reports_low_days_remaining(self):
        material = Cert__Generator().generate('1.1.1.1', days_valid=2)
        info     = Cert__Inspector().inspect_pem(material.cert_pem)
        assert info.is_expired is False
        assert info.days_remaining <= 2
