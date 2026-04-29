# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__User_Data__Builder
# Locks the placeholder contract + the install-step structure. Both compose
# YAML and the resolved interceptor source are taken as input.
# Caddy replaced nginx in the v0.1.118 caddy slice.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__User_Data__Builder          import (CADDY_DIR                ,
                                                                                              CADDY_DOCKERFILE         ,
                                                                                              CADDY_FILE               ,
                                                                                              CADDY_JWT_SECRET         ,
                                                                                              CADDY_USERS_JSON         ,
                                                                                              COMPOSE_DIR              ,
                                                                                              COMPOSE_FILE             ,
                                                                                              INTERCEPTOR_FILE         ,
                                                                                              LOG_FILE                 ,
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

    # ── install / Caddy artefact steps ────────────────────────────────────────

    def test_render__installs_docker_via_dnf(self):
        out = self._out()
        assert 'dnf install -y docker' in out
        assert 'httpd-tools'           in out                                       # for htpasswd (used to compute the bcrypt hash for users.json)

    def test_render__no_self_signed_openssl_step(self):                              # Caddy `tls internal` provisions its own cert; openssl no longer needed
        out = self._out()
        assert 'openssl req -x509' not in out

    def test_render__writes_caddy_dockerfile_and_caddyfile(self):
        out = self._out()
        assert f'cat > {CADDY_DOCKERFILE}' in out
        assert "<<'SG_VNC_CADDY_DOCKERFILE_EOF'" in out
        assert f'cat > {CADDY_FILE}'             in out
        assert "<<'SG_VNC_CADDYFILE_EOF'"        in out

    def test_render__writes_users_json_with_bcrypt_hash_from_htpasswd(self):
        out = self._out()
        assert 'htpasswd -bnBC 10 operator' in out                                  # `-n` = print to stdout (no file write); `-B` = bcrypt; `-C 10` = cost 10
        assert 'BCRYPT_HASH=$(htpasswd'      in out
        assert f'cat > {CADDY_USERS_JSON}'   in out

    def test_render__generates_jwt_signing_secret(self):
        out = self._out()
        assert '/dev/urandom'                in out
        assert f'> {CADDY_JWT_SECRET}'       in out

    def test_render__chmod_644_on_users_and_jwt(self):                              # Bind-mounted into the non-root caddy container; same constraint as the previous nginx setup
        out = self._out()
        assert f'chmod 644 {CADDY_USERS_JSON} {CADDY_JWT_SECRET}' in out

    def test_render__builds_caddy_image_before_compose_up(self):                    # First boot needs `docker compose build caddy` since image is local-only
        out = self._out()
        build_idx = out.index('docker compose build caddy')
        up_idx    = out.index('docker compose up -d')
        assert build_idx < up_idx

    def test_render__compose_up_runs_in_compose_dir(self):
        out = self._out()
        assert COMPOSE_DIR             in out
        assert 'docker compose up -d'  in out

    # ── secret hygiene ────────────────────────────────────────────────────────

    def test_render__operator_password_appears_only_in_env_var_assignment(self):
        out = self._out(password='SUPERSECRET-1234567890ab')
        assert out.count('SUPERSECRET-1234567890ab') == 1                            # The literal value should appear once (as the SG_VNC_OPERATOR_PASSWORD assignment line)
        assert "SG_VNC_OPERATOR_PASSWORD='SUPERSECRET-1234567890ab'" in out

    def test_render__compose_yaml_does_not_contain_password(self):                  # Defensive — secret never leaks to compose
        out = self._out(password='LEAKDETECT-1234567890ab')
        assert 'LEAKDETECT-1234567890ab' not in SAMPLE_COMPOSE_YAML

    def test_render__users_json_uses_shell_substitution_for_hash(self):             # The literal hash is computed by htpasswd at boot; the template emits ${BCRYPT_HASH} which the heredoc expands at runtime
        out = self._out()
        assert '${BCRYPT_HASH}' in out

    # ── contract ──────────────────────────────────────────────────────────────

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', USER_DATA_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)

    def test_canonical_paths_are_under_opt_sg_vnc(self):
        assert COMPOSE_DIR        == '/opt/sg-vnc'
        assert COMPOSE_FILE       == '/opt/sg-vnc/docker-compose.yml'
        assert INTERCEPTOR_FILE   == '/opt/sg-vnc/interceptors/runtime/active.py'
        assert CADDY_DIR          == '/opt/sg-vnc/caddy'
        assert CADDY_FILE         == '/opt/sg-vnc/caddy/Caddyfile'
        assert CADDY_USERS_JSON   == '/opt/sg-vnc/caddy/users.json'
        assert CADDY_JWT_SECRET   == '/opt/sg-vnc/caddy/jwt-secret'
        assert LOG_FILE           == '/var/log/sg-vnc-boot.log'
