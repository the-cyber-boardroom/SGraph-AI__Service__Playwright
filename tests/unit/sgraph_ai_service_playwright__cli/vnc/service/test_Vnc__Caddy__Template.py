# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Caddy__Template
# Locks the Dockerfile build pattern + the Caddyfile route shape +
# users.json identity-store schema for caddy-security.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Caddy__Template             import (CADDY_BUILDER_IMAGE     ,
                                                                                              CADDY_LOCAL_IMAGE_TAG   ,
                                                                                              CADDY_RUNTIME_IMAGE     ,
                                                                                              CADDY_SECURITY_VERSION  ,
                                                                                              Vnc__Caddy__Template    )


class test_render_dockerfile(TestCase):

    def setUp(self):
        self.tpl = Vnc__Caddy__Template()

    def test__two_stage_build(self):
        out = self.tpl.render_dockerfile()
        assert f'FROM {CADDY_BUILDER_IMAGE} AS builder' in out
        assert f'FROM {CADDY_RUNTIME_IMAGE}'             in out

    def test__includes_pinned_caddy_security_version(self):
        out = self.tpl.render_dockerfile()
        assert f'caddy-security@{CADDY_SECURITY_VERSION}' in out

    def test__copies_caddy_binary_into_runtime(self):
        out = self.tpl.render_dockerfile()
        assert 'COPY --from=builder /usr/bin/caddy /usr/bin/caddy' in out


class test_render_caddyfile(TestCase):

    def setUp(self):
        self.out = Vnc__Caddy__Template().render_caddyfile()

    def test__listens_on_443_with_internal_tls(self):
        assert ':443 {' in self.out
        assert 'tls internal' in self.out                                            # No openssl step in user-data — Caddy handles its own cert via internal CA

    def test__healthz_route_unauthenticated(self):                                   # Probe target — Vnc__HTTP__Probe hits this
        assert 'route /healthz' in self.out
        assert 'respond "ok" 200' in self.out

    def test__login_route_uses_authentication_portal(self):
        assert 'route /login*' in self.out
        assert 'authenticate with sg_portal' in self.out

    def test__mitmweb_route_strips_prefix_and_proxies(self):                          # /mitmweb/foo on the caddy → /foo on mitmweb:8081 (mitmweb has no /mitmweb base path)
        assert 'route /mitmweb/*'    in self.out
        assert 'uri strip_prefix /mitmweb' in self.out
        assert 'reverse_proxy mitmproxy:8081' in self.out

    def test__catchall_route_proxies_to_chromium(self):
        assert 'route /*' in self.out
        assert 'reverse_proxy chromium:3000' in self.out

    def test__authorization_protects_routes(self):
        assert 'authorization policy operator_policy' in self.out
        assert 'authorize with operator_policy'       in self.out
        assert 'allow roles authp/user'               in self.out

    def test__local_identity_store_points_at_users_json(self):
        assert 'local identity store local_users' in self.out
        assert 'path  /etc/caddy/users.json'      in self.out

    def test__jwt_secret_path_is_consistent(self):                                   # Same path used by portal sign and policy verify
        assert 'crypto key sign-verify from file /etc/caddy/jwt-secret' in self.out
        assert 'crypto key verify from file /etc/caddy/jwt-secret'      in self.out

    def test__cookie_attributes_are_secure(self):
        assert 'cookie httponly true' in self.out
        assert 'cookie secure   true' in self.out
        assert 'cookie samesite lax'  in self.out

    def test__token_lifetime_defaults_to_eight_hours(self):
        assert 'crypto default token lifetime 28800' in self.out                     # 8h work session


class test_render_users_json(TestCase):

    def setUp(self):
        self.tpl = Vnc__Caddy__Template()

    def test__embeds_bcrypt_hash(self):
        out = self.tpl.render_users_json(bcrypt_hash='$2y$10$abcdefghijklmnop')
        assert '$2y$10$abcdefghijklmnop' in out

    def test__user_role_is_authp_user(self):                                         # Matches Caddyfile `allow roles authp/user`
        out = self.tpl.render_users_json(bcrypt_hash='$2y$10$h')
        assert '"name": "user"'         in out
        assert '"organization": "authp"' in out

    def test__hardcoded_username_operator(self):                                     # Single-user model; matches CLI default --user operator
        out = self.tpl.render_users_json(bcrypt_hash='$2y$10$h')
        assert '"username"       : "operator"' in out


class test_constants(TestCase):

    def test__local_image_tag_is_namespaced(self):
        assert CADDY_LOCAL_IMAGE_TAG == 'sg-vnc/caddy:local'

    def test__caddy_security_version_is_pinned(self):                                # Project rule: no `latest` tags, including plugin versions
        assert CADDY_SECURITY_VERSION.startswith('v')
