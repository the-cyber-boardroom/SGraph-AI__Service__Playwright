# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__TLS / Routes__TLS
# Exercises the slim public TLS surface through a real TestClient: the cert-info
# endpoint (503 until a cert exists, decoded info once it does), the
# secure-context-check browser page, and the result POST → last GET round-trip.
# No api-key is sent — the app is public by design and the requests must pass.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi.testclient import TestClient

from sg_compute.fast_api.tls.Fast_API__TLS    import Fast_API__TLS
from sg_compute.platforms.tls.Cert__Generator import Cert__Generator

client = TestClient(Fast_API__TLS().setup().app())


class TestFastApiTls:

    def test_no_api_key_required(self):
        assert Fast_API__TLS().config.enable_api_key is False

    def test_cert_info_503_when_no_cert(self, monkeypatch):
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE', '/nonexistent/cert.pem')
        response = client.get('/tls/cert-info')
        assert response.status_code == 503

    def test_cert_info_decodes_real_cert(self, tmp_path, monkeypatch):
        cert_path = str(tmp_path / 'cert.pem')
        key_path  = str(tmp_path / 'key.pem')
        Cert__Generator().generate_to_files(cert_path, key_path, '1.2.3.4', sans=['vault.local'])
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE', cert_path)

        response = client.get('/tls/cert-info')
        assert response.status_code == 200
        body = response.json()
        assert body['is_self_signed'] is True
        assert body['is_expired']     is False
        assert 'CN=1.2.3.4'  in body['subject']
        assert '1.2.3.4'     in body['sans']
        assert 'vault.local' in body['sans']

    def test_secure_context_check_serves_html_page(self):
        response = client.get('/tls/secure-context-check')
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/html')
        text = response.text
        assert 'window.isSecureContext'        in text
        assert 'window.crypto'                 in text
        assert '/tls/secure-context-result'    in text

    def test_secure_context_result_roundtrip(self):
        payload = {'url'               : 'https://1.2.3.4/tls/secure-context-check',
                   'user_agent'        : 'pytest-agent',
                   'is_secure_context' : True,
                   'has_web_crypto'    : True,
                   'checked_at'        : 1_700_000_000_000}
        post = client.post('/tls/secure-context-result', json=payload)
        assert post.status_code == 200
        assert post.json() == {'recorded': True, 'is_secure_context': True}

        last = client.get('/tls/secure-context-last')
        assert last.status_code == 200
        body = last.json()
        assert body['recorded']          is True
        assert body['is_secure_context'] is True
        assert body['has_web_crypto']    is True
        assert body['user_agent']        == 'pytest-agent'

    def test_secure_context_result_records_failure(self):
        payload = {'url'               : 'http://1.2.3.4/tls/secure-context-check',
                   'user_agent'        : 'pytest-agent',
                   'is_secure_context' : False,
                   'has_web_crypto'    : False,
                   'checked_at'        : 1_700_000_000_000}
        post = client.post('/tls/secure-context-result', json=payload)
        assert post.status_code == 200
        assert post.json()['is_secure_context'] is False
