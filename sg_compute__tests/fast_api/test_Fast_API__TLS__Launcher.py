# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__TLS__Launcher (the §8.2 TLS launch contract)
# Env → Schema__Fast_API__TLS__Config → uvicorn kwargs, plus the fail-loud
# assertion when TLS is enabled but the cert files are missing. serve() itself
# (the thin uvicorn.run call) is not exercised.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute.fast_api.Fast_API__TLS__Launcher       import Fast_API__TLS__Launcher
from sg_compute.fast_api.Schema__Fast_API__TLS__Config import Schema__Fast_API__TLS__Config


class TestFastApiTlsLauncher:

    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv('FAST_API__TLS__ENABLED', raising=False)
        launcher = Fast_API__TLS__Launcher()
        config   = launcher.config_from_env()
        assert type(config) is Schema__Fast_API__TLS__Config
        assert config.enabled is False
        assert config.port    == 8000
        assert launcher.uvicorn_kwargs(config) == {'host': '0.0.0.0', 'port': 8000}

    def test_enabled_uses_tls_kwargs_and_default_port(self, monkeypatch):
        monkeypatch.setenv('FAST_API__TLS__ENABLED', 'true')
        monkeypatch.delenv('FAST_API__TLS__PORT',      raising=False)
        monkeypatch.delenv('FAST_API__TLS__CERT_FILE', raising=False)
        monkeypatch.delenv('FAST_API__TLS__KEY_FILE',  raising=False)
        launcher = Fast_API__TLS__Launcher()
        config   = launcher.config_from_env()
        assert config.enabled is True
        assert config.port    == 443
        kwargs = launcher.uvicorn_kwargs(config)
        assert kwargs['port']         == 443
        assert kwargs['ssl_certfile'] == '/certs/cert.pem'
        assert kwargs['ssl_keyfile']  == '/certs/key.pem'

    def test_enabled_respects_env_overrides(self, monkeypatch):
        monkeypatch.setenv('FAST_API__TLS__ENABLED',   '1')
        monkeypatch.setenv('FAST_API__TLS__PORT',      '8443')
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE', '/x/c.pem')
        monkeypatch.setenv('FAST_API__TLS__KEY_FILE',  '/x/k.pem')
        config = Fast_API__TLS__Launcher().config_from_env()
        assert config.port      == 8443
        assert config.cert_file == '/x/c.pem'
        assert config.key_file  == '/x/k.pem'

    def test_falsey_values_keep_tls_disabled(self, monkeypatch):
        for value in ('false', '0', 'no', ''):
            monkeypatch.setenv('FAST_API__TLS__ENABLED', value)
            assert Fast_API__TLS__Launcher().config_from_env().enabled is False

    def test_assert_ready_fails_loud_when_cert_missing(self, monkeypatch):
        monkeypatch.setenv('FAST_API__TLS__ENABLED',   'true')
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE', '/nonexistent/cert.pem')
        monkeypatch.setenv('FAST_API__TLS__KEY_FILE',  '/nonexistent/key.pem')
        launcher = Fast_API__TLS__Launcher()
        with pytest.raises(AssertionError):
            launcher.assert_ready(launcher.config_from_env())

    def test_assert_ready_passes_when_files_exist(self, tmp_path, monkeypatch):
        cert_path = tmp_path / 'c.pem'
        key_path  = tmp_path / 'k.pem'
        cert_path.write_text('cert')
        key_path.write_text('key')
        monkeypatch.setenv('FAST_API__TLS__ENABLED',   'true')
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE', str(cert_path))
        monkeypatch.setenv('FAST_API__TLS__KEY_FILE',  str(key_path))
        launcher = Fast_API__TLS__Launcher()
        launcher.assert_ready(launcher.config_from_env())              # must not raise

    def test_assert_ready_is_noop_when_disabled(self, monkeypatch):
        monkeypatch.delenv('FAST_API__TLS__ENABLED', raising=False)
        launcher = Fast_API__TLS__Launcher()
        launcher.assert_ready(launcher.config_from_env())              # must not raise
