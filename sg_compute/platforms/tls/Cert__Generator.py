# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cert__Generator
# Generates a self-signed X.509 cert + RSA key (PEM) for a given common name.
# Used by the one-shot cert sidecar to seed /certs before the TLS apps boot.
#
# common_name doubles as a SAN entry — an IP literal becomes an IPAddress SAN,
# anything else a DNSName SAN — so the cert is valid for https://<ip> directly.
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress
import os
from datetime import datetime, timedelta, timezone
from typing   import List, Optional

from cryptography                                import x509
from cryptography.hazmat.primitives              import hashes, serialization
from cryptography.hazmat.primitives.asymmetric   import rsa
from cryptography.x509.oid                       import NameOID
from osbot_utils.type_safe.Type_Safe             import Type_Safe

from sg_compute.platforms.tls.Schema__Cert__Material import Schema__Cert__Material

DEFAULT_DAYS_VALID = 160                                 # mirrors the LE shortlived profile ceiling


def _san_entry(value: str):
    try:
        return x509.IPAddress(ipaddress.ip_address(value))
    except ValueError:
        return x509.DNSName(value)


class Cert__Generator(Type_Safe):

    def generate(self, common_name : str                 ,
                       sans        : Optional[List[str]] = None ,
                       days_valid  : int                 = DEFAULT_DAYS_VALID) -> Schema__Cert__Material:
        key  = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])

        san_values = list(dict.fromkeys([common_name] + list(sans or [])))   # dedupe, keep order
        san        = x509.SubjectAlternativeName([_san_entry(v) for v in san_values])

        now  = datetime.now(timezone.utc).replace(tzinfo=None)               # cryptography <42 wants naive UTC
        cert = (x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5))                # small backdate for clock skew
                .not_valid_after(now + timedelta(days=days_valid))
                .add_extension(san, critical=False)
                .sign(key, hashes.SHA256()))

        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem  = key.private_bytes(encoding             = serialization.Encoding.PEM           ,
                                     format               = serialization.PrivateFormat.PKCS8    ,
                                     encryption_algorithm  = serialization.NoEncryption()         ).decode()
        return Schema__Cert__Material(cert_pem=cert_pem, key_pem=key_pem)

    def generate_to_files(self, cert_path   : str                 ,
                                key_path    : str                 ,
                                common_name : str                 ,
                                sans        : Optional[List[str]] = None ,
                                days_valid  : int                 = DEFAULT_DAYS_VALID) -> Schema__Cert__Material:
        material = self.generate(common_name, sans=sans, days_valid=days_valid)
        for path in (cert_path, key_path):
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        with open(cert_path, 'w') as f:
            f.write(material.cert_pem)
        with open(key_path, 'w') as f:
            f.write(material.key_pem)
        os.chmod(key_path,  0o600)                                           # private key — owner-only
        os.chmod(cert_path, 0o644)
        return material
