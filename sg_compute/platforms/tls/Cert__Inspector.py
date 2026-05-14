# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cert__Inspector
# Decodes an X.509 certificate into Schema__Cert__Info. Three sources:
#   inspect_pem  — raw PEM bytes/str already in hand
#   inspect_file — a PEM file on disk
#   inspect_host — a live TLS handshake against host:port (the cert as served)
# Mirrors the cryptography.x509 usage already proven in mitmproxy Routes__CA.
# ═══════════════════════════════════════════════════════════════════════════════

import ssl
from datetime import datetime, timezone

from cryptography                     import x509
from cryptography.hazmat.primitives   import hashes
from osbot_utils.type_safe.Type_Safe  import Type_Safe

from sg_compute.platforms.tls.Schema__Cert__Info import Schema__Cert__Info


def _dt_to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:                                                    # cryptography <42 returns naive UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


class Cert__Inspector(Type_Safe):

    def inspect_pem(self, pem, source: str = '') -> Schema__Cert__Info:
        pem_bytes = pem.encode() if isinstance(pem, str) else pem
        cert      = x509.load_pem_x509_certificate(pem_bytes)

        not_before_dt = getattr(cert, 'not_valid_before_utc', None) or cert.not_valid_before
        not_after_dt  = getattr(cert, 'not_valid_after_utc',  None) or cert.not_valid_after
        not_before    = _dt_to_ms(not_before_dt)
        not_after     = _dt_to_ms(not_after_dt)

        now_ms         = int(datetime.now(timezone.utc).timestamp() * 1000)
        days_remaining = (not_after - now_ms) // (86400 * 1000)

        try:
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            sans    = [str(v) for v in san_ext.value.get_values_for_type(x509.DNSName)] + \
                      [str(v) for v in san_ext.value.get_values_for_type(x509.IPAddress)]
        except x509.ExtensionNotFound:
            sans = []

        digest = cert.fingerprint(hashes.SHA256())
        return Schema__Cert__Info(source             = source                                          ,
                                  subject            = cert.subject.rfc4514_string()                   ,
                                  issuer             = cert.issuer.rfc4514_string()                    ,
                                  serial             = str(cert.serial_number)                        ,
                                  fingerprint_sha256 = ':'.join(f'{b:02X}' for b in digest)            ,
                                  sans               = sans                                            ,
                                  not_before         = not_before                                     ,
                                  not_after          = not_after                                      ,
                                  days_remaining     = int(days_remaining)                            ,
                                  is_self_signed     = cert.subject == cert.issuer                    ,
                                  is_expired         = now_ms > not_after                              )

    def inspect_file(self, path: str) -> Schema__Cert__Info:
        with open(path, 'rb') as f:
            return self.inspect_pem(f.read(), source=f'file:{path}')

    def inspect_host(self, host: str, port: int = 443) -> Schema__Cert__Info:
        pem = ssl.get_server_certificate((host, port))                       # handshake; returns the leaf cert as PEM
        return self.inspect_pem(pem, source=f'host:{host}:{port}')
