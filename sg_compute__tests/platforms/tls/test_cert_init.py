# ═══════════════════════════════════════════════════════════════════════════════
# Tests — cert_init (one-shot cert sidecar entry point)
# Common-name resolution precedence + the full write path. The IMDS fallback
# path is not exercised — it needs the EC2 metadata endpoint.
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest

from sg_compute.platforms.tls               import cert_init
from sg_compute.platforms.tls.Cert__Inspector import Cert__Inspector


class TestCertInit:

    def test_resolve_common_name_env_wins(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__COMMON_NAME', '5.6.7.8')
        assert cert_init.resolve_common_name() == '5.6.7.8'

    def test_main_writes_cert_with_cn_and_sans(self, tmp_path, monkeypatch):
        cert_path = str(tmp_path / 'cert.pem')
        key_path  = str(tmp_path / 'key.pem')
        monkeypatch.setenv('SG__CERT_INIT__COMMON_NAME', '10.0.0.1')
        monkeypatch.setenv('SG__CERT_INIT__SANS',        'a.local,b.local')
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE',   cert_path)
        monkeypatch.setenv('FAST_API__TLS__KEY_FILE',    key_path)

        cert_init.main()

        assert os.path.isfile(cert_path)
        assert os.path.isfile(key_path)
        info = Cert__Inspector().inspect_file(cert_path)
        assert 'CN=10.0.0.1' in info.subject
        assert '10.0.0.1'    in info.sans
        assert 'a.local'     in info.sans
        assert 'b.local'     in info.sans

    def test_main_self_signed_mode_explicit(self, tmp_path, monkeypatch):
        cert_path = str(tmp_path / 'cert.pem')
        key_path  = str(tmp_path / 'key.pem')
        monkeypatch.setenv('SG__CERT_INIT__MODE',        'self-signed')
        monkeypatch.setenv('SG__CERT_INIT__COMMON_NAME', '10.0.0.2')
        monkeypatch.setenv('FAST_API__TLS__CERT_FILE',   cert_path)
        monkeypatch.setenv('FAST_API__TLS__KEY_FILE',    key_path)
        cert_init.main()
        assert os.path.isfile(cert_path)

    def test_main_unknown_mode_exits_non_zero(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__MODE', 'banana')
        with pytest.raises(SystemExit) as exc:
            cert_init.main()
        assert exc.value.code != 0

    def test_resolve_public_ip_accepts_a_valid_ip(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__COMMON_NAME', '13.40.119.90')
        assert cert_init.resolve_public_ip() == '13.40.119.90'

    def test_resolve_public_ip_rejects_a_non_ip(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__COMMON_NAME', 'not-an-ip')
        with pytest.raises(RuntimeError):
            cert_init.resolve_public_ip()

    def test_resolve_tls_hostname_accepts_a_valid_fqdn(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__TLS_HOSTNAME', 'test-2.sg-compute.sgraph.ai')
        assert cert_init.resolve_tls_hostname() == 'test-2.sg-compute.sgraph.ai'

    def test_resolve_tls_hostname_strips_surrounding_whitespace(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__TLS_HOSTNAME', '  vault.example.com  ')
        assert cert_init.resolve_tls_hostname() == 'vault.example.com'

    def test_resolve_tls_hostname_rejects_empty(self, monkeypatch):
        monkeypatch.delenv('SG__CERT_INIT__TLS_HOSTNAME', raising=False)
        with pytest.raises(RuntimeError, match='needs SG__CERT_INIT__TLS_HOSTNAME'):
            cert_init.resolve_tls_hostname()

    def test_resolve_tls_hostname_rejects_an_ip(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__TLS_HOSTNAME', '18.134.9.182')
        with pytest.raises(RuntimeError, match='is an IP — use letsencrypt-ip mode'):
            cert_init.resolve_tls_hostname()

    def test_resolve_tls_hostname_rejects_a_url(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__TLS_HOSTNAME', 'https://vault.example.com/foo')
        with pytest.raises(RuntimeError, match='bare FQDN'):
            cert_init.resolve_tls_hostname()

    def test_resolve_tls_hostname_rejects_a_hostport(self, monkeypatch):
        monkeypatch.setenv('SG__CERT_INIT__TLS_HOSTNAME', 'vault.example.com:443')
        with pytest.raises(RuntimeError, match='bare FQDN'):
            cert_init.resolve_tls_hostname()

    def test_main_letsencrypt_hostname_validates_envs_before_network(self, monkeypatch):
        # letsencrypt-hostname mode should fail loud, locally, when the FQDN env is missing —
        # before any LE call. This protects an unattended boot from hitting LE rate limits.
        monkeypatch.setenv('SG__CERT_INIT__MODE', 'letsencrypt-hostname')
        monkeypatch.delenv('SG__CERT_INIT__TLS_HOSTNAME', raising=False)
        with pytest.raises(RuntimeError, match='needs SG__CERT_INIT__TLS_HOSTNAME'):
            cert_init.main()

    def test_wait_for_dns_returns_immediately_when_already_matched(self):
        # Common case when --with-aws-dns ran the Route 53 INSYNC wait in parallel —
        # cert-init's first poll should see the FQDN already pointing at our IP.
        ticks = []
        cert_init.wait_for_dns_to_match(hostname='vault.example.com',
                                        my_ip='18.0.0.1',
                                        timeout_sec=10,
                                        poll_sec=0,
                                        now_fn      = lambda: 0.0,                  # never advances — we should not consult time again after the first match
                                        sleep_fn    = lambda s: ticks.append(s),
                                        resolve_fn  = lambda h: '18.0.0.1')
        assert ticks == []                                                          # no sleep ever — converged on first poll

    def test_wait_for_dns_converges_after_a_few_polls(self):
        # Simulate the propagation window: first two polls see the old/empty answer,
        # third poll sees the new IP. The function must return cleanly without timing out.
        answers = iter(['<resolution failed: NXDOMAIN>',
                        '1.2.3.4',                                                  # old A record still cached
                        '18.0.0.1'])                                                # propagated
        clock   = [0.0]
        sleeps  = []
        def now():
            clock[0] += 1
            return clock[0]
        cert_init.wait_for_dns_to_match(hostname='vault.example.com',
                                        my_ip='18.0.0.1',
                                        timeout_sec=60,
                                        poll_sec=2,
                                        now_fn      = now,
                                        sleep_fn    = lambda s: sleeps.append(s),
                                        resolve_fn  = lambda h: next(answers))
        assert sleeps == [2, 2]                                                     # two retries before the third poll matched

    def test_wait_for_dns_raises_on_timeout(self):
        clock = [0.0]
        def now():
            clock[0] += 10                                                          # each call to now() advances 10s — 5 calls → timeout
            return clock[0]
        with pytest.raises(RuntimeError, match='did not converge'):
            cert_init.wait_for_dns_to_match(hostname='vault.example.com',
                                            my_ip='18.0.0.1',
                                            timeout_sec=30,
                                            poll_sec=0,
                                            now_fn      = now,
                                            sleep_fn    = lambda s: None,
                                            resolve_fn  = lambda h: '1.2.3.4')      # never matches

    def test_resolve_hostname_handles_nxdomain_as_a_sentinel(self):
        # Internal helper used by main() — must NEVER raise gaierror up to callers;
        # returns a sentinel string so the polling loop keeps going.
        sentinel = cert_init._resolve_hostname('definitely-not-a-real-domain-' + 'x' * 40 + '.invalid')
        assert sentinel.startswith('<resolution failed:')
