# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy/fast_api/routes/Routes__CA.py
#
# Creates a self-signed cert in a temp file, points the CA_CERT_PATH env var
# at it, and asserts /ca/cert + /ca/info return the expected bytes/metadata.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime
import hashlib
import os
import tempfile
from unittest                                                                        import TestCase

from cryptography                                                                    import x509
from cryptography.hazmat.primitives                                                  import hashes, serialization
from cryptography.hazmat.primitives.asymmetric                                       import rsa
from cryptography.x509.oid                                                           import NameOID
from fastapi.testclient                                                              import TestClient

from agent_mitmproxy.consts                                                          import env_vars
from agent_mitmproxy.fast_api.Fast_API__Agent_Mitmproxy                              import Fast_API__Agent_Mitmproxy


API_KEY_NAME  = 'X-API-Key'
API_KEY_VALUE = 'test-key-ca'


def _write_self_signed_pem(path: str) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'agent-mitmproxy-test')])
    cert = (x509.CertificateBuilder()
            .subject_name (subject)
            .issuer_name  (issuer )
            .public_key   (key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1 ))
            .not_valid_after (now + datetime.timedelta(days=30))
            .sign(key, hashes.SHA256()))
    pem = cert.public_bytes(serialization.Encoding.PEM)
    with open(path, 'wb') as f:
        f.write(pem)
    return pem


class test_Routes__CA(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
        cls.tmp.close()
        cls.pem_bytes = _write_self_signed_pem(cls.tmp.name)
        os.environ[env_vars.ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[env_vars.ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        os.environ[env_vars.ENV_VAR__CA_CERT_PATH ] = cls.tmp.name
        cls.client = TestClient(Fast_API__Agent_Mitmproxy().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(env_vars.ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(env_vars.ENV_VAR__API_KEY_VALUE, None)
        os.environ.pop(env_vars.ENV_VAR__CA_CERT_PATH , None)
        os.unlink(cls.tmp.name)

    def _headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test__cert_returns_pem_bytes(self):
        response = self.client.get('/ca/cert', headers=self._headers())
        assert response.status_code            == 200
        assert response.headers['content-type'] == 'application/x-pem-file'
        assert response.content                 == self.pem_bytes

    def test__info_returns_metadata(self):
        response = self.client.get('/ca/info', headers=self._headers())
        assert response.status_code == 200
        body = response.json()
        expected_fp = ':'.join(f'{b:02X}' for b in hashlib.sha256(b'').digest())     # Placeholder — we don't hash the PEM, we hash the DER. Recompute properly:
        # Use cryptography to compute the expected DER-sha256
        cert = x509.load_pem_x509_certificate(self.pem_bytes)
        expected_fp = ':'.join(f'{b:02X}' for b in cert.fingerprint(hashes.SHA256()))
        assert body['path'              ].endswith('.pem')
        assert body['size_bytes'        ] == len(self.pem_bytes)
        assert body['fingerprint_sha256'] == expected_fp
        assert body['not_before'        ] <  body['not_after']

    def test__cert_missing_returns_503(self):
        original = os.environ[env_vars.ENV_VAR__CA_CERT_PATH]
        try:
            os.environ[env_vars.ENV_VAR__CA_CERT_PATH] = '/tmp/definitely-not-here.pem'
            response = self.client.get('/ca/cert', headers=self._headers())
            assert response.status_code == 503
        finally:
            os.environ[env_vars.ENV_VAR__CA_CERT_PATH] = original
