# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: user-data builder render tests (pure)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request   import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.service.Content_Proxy__User_Data__Builder        import (Content_Proxy__User_Data__Builder,
                                                                                             APP_DIR, PLACEHOLDERS)


class test_Content_Proxy__User_Data__Builder(TestCase):

    def setUp(self):
        self.req = Schema__Content_Proxy__Create__Request(proxyauth_user='demo',
                                                          proxyauth_pass='secret',
                                                          max_hours=2)
        self.ud  = Content_Proxy__User_Data__Builder().render(self.req)

    def test_installs_docker_and_compose_up(self):
        assert 'dnf install -y docker'        in self.ud
        assert 'docker compose --env-file'    in self.ud
        assert 'up -d'                        in self.ud

    def test_writes_compose_with_both_proxies(self):
        assert f'{APP_DIR}/docker-compose.yml' in self.ud
        assert self.ud.count('--scripts=/interceptors/active.py') == 2              # embedded compose has both proxies
        assert 'cp-vault-app' in self.ud

    def test_writes_env_with_secrets(self):
        assert 'CONTENT_PROXY__PROXYAUTH_USER=demo'   in self.ud
        assert 'CONTENT_PROXY__PROXYAUTH_PASS=secret' in self.ud

    def test_embeds_interceptor_files(self):
        assert f'{APP_DIR}/interceptors/active.py' in self.ud
        assert 'Content-Proxy interceptor loaded'  in self.ud                       # active.py body embedded
        assert 'def should_process_request'        in self.ud                       # logic module body embedded

    def test_shutdown_for_max_hours(self):
        assert 'shutdown -h +120' in self.ud                                        # 2h → 120 min

    def test_no_shutdown_when_max_hours_zero(self):
        ud = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(max_hours=0))
        assert 'no auto-terminate' in ud

    def test_mvp_has_no_vaults(self):
        assert 'load-vaults' not in self.ud
        assert 'sgit clone'  not in self.ud

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('log_file', 'app_dir', 'env_body', 'compose_body',
                                'active_body', 'logic_body', 'ca_block', 'shutdown_line')
