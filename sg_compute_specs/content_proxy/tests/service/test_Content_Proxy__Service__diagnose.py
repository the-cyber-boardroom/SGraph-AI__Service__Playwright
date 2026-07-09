# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: diagnose() pure parsers
# No AWS/SSM — exercises the stdout/boot-log parsers the diagnose generator hands
# raw SSM output to (which cp-* containers are up, cert-init exit state, boot-log
# failed/complete). Mirrors sg va's testable-parser split.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                   import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                    import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.service.Content_Proxy__Service                    import (BASE_CONTAINERS, BOOT_LOG,
                                                                                            expected_containers, has_cert_init,
                                                                                            parse_ps_names_status, containers_up_status,
                                                                                            engine_active, boot_log_failed,
                                                                                            boot_log_complete, boot_log_last_stage,
                                                                                            cert_init_status)


class test_expected_containers(TestCase):

    def test_plain_stack_is_base_set_only(self):
        exp = expected_containers(Enum__Content_Proxy__Tls.NONE, Enum__Content_Proxy__Edge.NONE)
        assert exp == BASE_CONTAINERS
        assert 'cp-cert-init' not in exp
        assert 'cp-caddy'     not in exp

    def test_tls_self_signed_adds_cert_init(self):
        exp = expected_containers(Enum__Content_Proxy__Tls.SELF_SIGNED, Enum__Content_Proxy__Edge.NONE)
        assert 'cp-cert-init' in exp
        assert 'cp-caddy'     not in exp

    def test_letsencrypt_adds_cert_init(self):
        exp = expected_containers(Enum__Content_Proxy__Tls.LETSENCRYPT, Enum__Content_Proxy__Edge.NONE)
        assert 'cp-cert-init' in exp

    def test_caddy_adds_caddy_not_cert_init(self):                                   # caddy self-manages TLS — no cert-init sidecar
        exp = expected_containers(Enum__Content_Proxy__Tls.NONE, Enum__Content_Proxy__Edge.CADDY)
        assert 'cp-caddy'     in exp
        assert 'cp-cert-init' not in exp

    def test_caddy_wins_over_tls_mode(self):                                         # caddy edge → no cert-init even if a tls mode set
        exp = expected_containers(Enum__Content_Proxy__Tls.LETSENCRYPT, Enum__Content_Proxy__Edge.CADDY)
        assert 'cp-caddy'     in exp
        assert 'cp-cert-init' not in exp


class test_has_cert_init(TestCase):

    def test_self_signed_non_caddy(self):
        assert has_cert_init(Enum__Content_Proxy__Tls.SELF_SIGNED, Enum__Content_Proxy__Edge.NONE) is True

    def test_letsencrypt_non_caddy(self):
        assert has_cert_init(Enum__Content_Proxy__Tls.LETSENCRYPT, Enum__Content_Proxy__Edge.NONE) is True

    def test_none_has_no_cert_init(self):
        assert has_cert_init(Enum__Content_Proxy__Tls.NONE, Enum__Content_Proxy__Edge.NONE) is False

    def test_caddy_never_has_cert_init(self):
        assert has_cert_init(Enum__Content_Proxy__Tls.LETSENCRYPT, Enum__Content_Proxy__Edge.CADDY) is False


class test_parse_ps_names_status(TestCase):

    def test_tab_separated(self):
        out = parse_ps_names_status('cp-vault-app\tUp 3 minutes\ncp-mitm-service\tUp 2 minutes')
        assert out == {'cp-vault-app': 'Up 3 minutes', 'cp-mitm-service': 'Up 2 minutes'}

    def test_whitespace_separated_fallback(self):                                   # no tab → split on first run of spaces
        out = parse_ps_names_status('cp-caddy   Exited (0) 1 minute ago')
        assert out == {'cp-caddy': 'Exited (0) 1 minute ago'}

    def test_blank_lines_ignored(self):
        out = parse_ps_names_status('\n\ncp-vault-app\tUp\n\n')
        assert out == {'cp-vault-app': 'Up'}

    def test_empty_string(self):
        assert parse_ps_names_status('') == {}


class test_containers_up_status(TestCase):

    def test_all_up(self):
        ps = ('cp-mitm-service\tUp\ncp-mitmproxy-int\tUp\ncp-mitmproxy-ext\tUp\n'
              'cp-sg-playwright\tUp\ncp-vault-app\tUp 5 minutes')
        all_up, up, down = containers_up_status(ps, BASE_CONTAINERS)
        assert all_up is True
        assert set(up)   == set(BASE_CONTAINERS)
        assert down == []

    def test_some_down(self):
        ps = 'cp-mitm-service\tUp\ncp-vault-app\tUp'
        all_up, up, down = containers_up_status(ps, BASE_CONTAINERS)
        assert all_up is False
        assert set(up) == {'cp-mitm-service', 'cp-vault-app'}
        assert 'cp-sg-playwright' in down

    def test_missing_entirely_counts_as_down(self):
        all_up, up, down = containers_up_status('', BASE_CONTAINERS)
        assert all_up is False
        assert set(down) == set(BASE_CONTAINERS)

    def test_cert_init_exited_zero_is_up(self):                                     # one-shot sidecar: clean exit IS healthy
        expected = BASE_CONTAINERS + ('cp-cert-init',)
        ps = ('cp-mitm-service\tUp\ncp-mitmproxy-int\tUp\ncp-mitmproxy-ext\tUp\n'
              'cp-sg-playwright\tUp\ncp-vault-app\tUp\ncp-cert-init\tExited (0) 2 minutes ago')
        all_up, up, down = containers_up_status(ps, expected)
        assert all_up is True
        assert 'cp-cert-init' in up

    def test_cert_init_exited_nonzero_is_down(self):
        expected = BASE_CONTAINERS + ('cp-cert-init',)
        ps = ('cp-mitm-service\tUp\ncp-mitmproxy-int\tUp\ncp-mitmproxy-ext\tUp\n'
              'cp-sg-playwright\tUp\ncp-vault-app\tUp\ncp-cert-init\tExited (1) 2 minutes ago')
        all_up, up, down = containers_up_status(ps, expected)
        assert all_up is False
        assert 'cp-cert-init' in down


class test_engine_active(TestCase):

    def test_active(self):
        assert engine_active('active') is True
        assert engine_active('  active\n') is True

    def test_inactive(self):
        assert engine_active('inactive') is False
        assert engine_active('activating') is False
        assert engine_active('') is False


class test_boot_log_failed(TestCase):

    def test_command_not_found(self):
        assert boot_log_failed('docker: command not found') is True

    def test_error_response_from_daemon(self):
        assert boot_log_failed('Error response from daemon: no such image') is True

    def test_complete_marker_clears_earlier_noise(self):                            # success marker wins
        assert boot_log_failed('failed to pull\n[content-proxy] boot complete at x') is False

    def test_clean_log_not_failed(self):
        assert boot_log_failed('[content-proxy] boot starting\npulling images') is False

    def test_empty(self):
        assert boot_log_failed('') is False


class test_boot_log_complete(TestCase):

    def test_complete(self):
        assert boot_log_complete('[content-proxy] boot complete at 2026-06-23') is True

    def test_not_complete(self):
        assert boot_log_complete('[content-proxy] boot starting') is False


class test_boot_log_last_stage(TestCase):

    def test_returns_last_marker_line(self):
        log = ('[content-proxy] boot starting at x\n'
               'dnf install -y docker\n'
               '[content-proxy] writing Caddyfile (edge=caddy)\n'
               'pulling…')
        assert boot_log_last_stage(log) == '[content-proxy] writing Caddyfile (edge=caddy)'

    def test_no_markers(self):
        assert boot_log_last_stage('just noise\nmore noise') == ''


class test_cert_init_status(TestCase):

    def test_missing_container_warns(self):
        status, detail = cert_init_status('cp-vault-app\tUp')
        assert status == 'warn'
        assert 'not yet' in detail

    def test_exited_zero_ok(self):
        status, detail = cert_init_status('cp-cert-init\tExited (0) 1 minute ago')
        assert status == 'ok'

    def test_exited_nonzero_fail(self):
        status, detail = cert_init_status('cp-cert-init\tExited (1) 5 seconds ago')
        assert status == 'fail'
        assert 'non-zero' in detail

    def test_still_running_warns(self):
        status, detail = cert_init_status('cp-cert-init\tUp 10 seconds')
        assert status == 'warn'
        assert 'still running' in detail


class test_boot_log_constant(TestCase):

    def test_points_at_content_proxy_boot_log(self):
        assert BOOT_LOG == '/var/log/sg-content-proxy-boot.log'
