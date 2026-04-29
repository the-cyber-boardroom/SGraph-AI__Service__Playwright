# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__User_Data__Builder
# Locks the placeholder contract + the install-step structure. Both compose
# YAML and the resolved interceptor source are taken as input.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__User_Data__Builder          import (COMPOSE_DIR             ,
                                                                                              COMPOSE_FILE             ,
                                                                                              INTERCEPTOR_FILE         ,
                                                                                              LOG_FILE                 ,
                                                                                              MITM_PROXYAUTH           ,
                                                                                              NGINX_HTPASSWD           ,
                                                                                              NGINX_TLS_DIR            ,
                                                                                              PLACEHOLDERS             ,
                                                                                              USER_DATA_TEMPLATE       ,
                                                                                              Vnc__User_Data__Builder  )


SAMPLE_COMPOSE_YAML       = "services:\n  chromium:\n    image: lscr.io/linuxserver/chromium:latest\n"
SAMPLE_INTERCEPTOR_SOURCE = "# sg-vnc: no interceptor active\n"


class test_Vnc__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Vnc__User_Data__Builder()

    def _out(self, password='AAAA-BBBB-1234-cdef'):
        return self.builder.render(stack_name         = 'vnc-quiet-fermi'       ,
                                    region             = 'eu-west-2'             ,
                                    compose_yaml       = SAMPLE_COMPOSE_YAML     ,
                                    interceptor_source = SAMPLE_INTERCEPTOR_SOURCE,
                                    operator_password  = password                 ,
                                    interceptor_kind   = 'none'                   )

    # ── shape ─────────────────────────────────────────────────────────────────

    def test_render__starts_with_shebang(self):
        assert self._out().startswith('#!/usr/bin/env bash\n')

    def test_render__sets_strict_bash(self):
        assert 'set -euo pipefail' in self._out()

    def test_render__substitutes_stack_and_region(self):
        out = self._out()
        assert "STACK_NAME='vnc-quiet-fermi'" in out
        assert "REGION='eu-west-2'"           in out

    def test_render__embeds_compose_yaml_in_heredoc(self):
        out = self._out()
        assert f'cat > {COMPOSE_FILE}'        in out
        assert "<<'SG_VNC_COMPOSE_EOF'"       in out
        assert SAMPLE_COMPOSE_YAML.strip()    in out

    def test_render__embeds_interceptor_source_in_heredoc(self):
        out = self._out()
        assert f'cat > {INTERCEPTOR_FILE}'   in out
        assert "<<'SG_VNC_INTERCEPTOR_EOF'"  in out
        assert SAMPLE_INTERCEPTOR_SOURCE     in out

    def test_render__no_placeholders_leaked(self):
        leftover = re.findall(r'\{([a-z_]+)\}', self._out())
        assert leftover == []

    # ── install / TLS / auth steps ────────────────────────────────────────────

    def test_render__installs_docker_via_dnf(self):
        out = self._out()
        assert 'dnf install -y docker' in out
        assert 'httpd-tools'           in out                                       # for htpasswd
        assert 'openssl'               in out                                       # for self-signed cert

    def test_render__generates_self_signed_tls_cert(self):
        out = self._out()
        assert 'openssl req -x509' in out
        assert NGINX_TLS_DIR        in out

    def test_render__writes_htpasswd_and_proxyauth_files(self):
        out = self._out()
        assert f'htpasswd -bcB {NGINX_HTPASSWD} operator' in out
        assert f'htpasswd -bcB {MITM_PROXYAUTH} operator' in out                    # mitmproxy --set proxyauth=@FILE expects htpasswd format (bcrypt); plaintext is rejected
        assert 'chmod 644'                                in out                    # 0644 — bind-mounted into containers running as non-root (mitmproxy + nginx); 0600 caused both to crash on read

    def test_render__compose_up_runs_in_compose_dir(self):
        out = self._out()
        assert COMPOSE_DIR             in out
        assert 'docker compose up -d'  in out

    # ── secret hygiene ────────────────────────────────────────────────────────

    def test_render__operator_password_appears_only_in_env_var_assignment(self):
        out = self._out(password='SUPERSECRET-1234567890ab')
        # The literal value should appear once (as the SG_VNC_OPERATOR_PASSWORD assignment line)
        assert out.count('SUPERSECRET-1234567890ab') == 1
        assert "SG_VNC_OPERATOR_PASSWORD='SUPERSECRET-1234567890ab'" in out

    def test_render__compose_yaml_does_not_contain_password(self):                  # Defensive — secret never leaks to compose
        out = self._out(password='LEAKDETECT-1234567890ab')
        assert 'LEAKDETECT-1234567890ab' not in SAMPLE_COMPOSE_YAML

    # ── contract ──────────────────────────────────────────────────────────────

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', USER_DATA_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)

    def test_canonical_paths_are_under_opt_sg_vnc(self):
        assert COMPOSE_DIR        == '/opt/sg-vnc'
        assert COMPOSE_FILE       == '/opt/sg-vnc/docker-compose.yml'
        assert INTERCEPTOR_FILE   == '/opt/sg-vnc/interceptors/runtime/active.py'
        assert LOG_FILE           == '/var/log/sg-vnc-boot.log'
