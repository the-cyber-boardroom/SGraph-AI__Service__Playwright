# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cert__Generator
# Self-signed cert generation: PEM shape, SAN handling (IP vs DNS), file output
# with correct permissions. No mocks — real cryptography end to end.
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress
import os

from cryptography import x509

from sg_compute.platforms.tls.Cert__Generator       import Cert__Generator
from sg_compute.platforms.tls.Schema__Cert__Material import Schema__Cert__Material


class TestCertGenerator:

    def test_generate_returns_pem_material(self):
        material = Cert__Generator().generate('example.local')
        assert type(material) is Schema__Cert__Material
        assert '-----BEGIN CERTIFICATE-----' in material.cert_pem
        assert '-----BEGIN PRIVATE KEY-----' in material.key_pem

    def test_ip_common_name_becomes_ip_san(self):
        material = Cert__Generator().generate('1.2.3.4')
        cert     = x509.load_pem_x509_certificate(material.cert_pem.encode())
        san      = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        assert ipaddress.ip_address('1.2.3.4') in san.get_values_for_type(x509.IPAddress)

    def test_dns_common_name_becomes_dns_san(self):
        material = Cert__Generator().generate('vault.local')
        cert     = x509.load_pem_x509_certificate(material.cert_pem.encode())
        san      = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        assert 'vault.local' in san.get_values_for_type(x509.DNSName)

    def test_extra_sans_appended_and_deduped(self):
        material = Cert__Generator().generate('host.local', sans=['host.local', 'other.local'])
        cert     = x509.load_pem_x509_certificate(material.cert_pem.encode())
        dns      = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value \
                       .get_values_for_type(x509.DNSName)
        assert 'host.local'  in dns
        assert 'other.local' in dns
        assert dns.count('host.local') == 1                            # common_name not duplicated into SANs

    def test_generate_to_files_writes_with_locked_down_key(self, tmp_path):
        cert_path = str(tmp_path / 'nested' / 'cert.pem')
        key_path  = str(tmp_path / 'nested' / 'key.pem')
        Cert__Generator().generate_to_files(cert_path, key_path, '9.9.9.9')
        assert os.path.isfile(cert_path)
        assert os.path.isfile(key_path)
        assert oct(os.stat(key_path).st_mode)[-3:]  == '600'           # private key — owner-only
        assert oct(os.stat(cert_path).st_mode)[-3:] == '644'
