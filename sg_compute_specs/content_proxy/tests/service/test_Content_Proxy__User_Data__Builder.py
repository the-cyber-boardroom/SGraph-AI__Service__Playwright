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

    def test_generated_app_keys_and_region_in_env(self):
        ud = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(scripts_bucket='my-scripts'),
            fastapi_api_key='FK123', playwright_api_key='PK456', region='eu-west-2',
            aws_creds={'AWS_ACCESS_KEY_ID': 'AKIA', 'AWS_SECRET_ACCESS_KEY': 'sk'})
        assert 'FASTAPI_API_KEY_VALUE=FK123'        in ud
        assert 'SG_PLAYWRIGHT__API_KEY=PK456'       in ud
        assert 'AWS_DEFAULT_REGION=eu-west-2'       in ud
        assert 'CACHE__SERVICE__BUCKET_NAME=my-scripts' in ud
        assert 'AWS_ACCESS_KEY_ID=AKIA'             in ud                            # forwarded creds (parity path)
        assert 'AWS_SECRET_ACCESS_KEY=sk'           in ud

    def test_no_aws_creds_baked_by_default(self):
        ud = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(), region='eu-west-2')            # no aws_creds → instance role
        assert 'AWS_ACCESS_KEY_ID='   not in ud
        assert 'AWS_SECRET_ACCESS_KEY=' not in ud

    def test_certs_dir_is_writable(self):
        assert 'chmod 777' in self.ud and '/certs' in self.ud                       # mitmproxy self-gen CA on EC2

    def test_proxy_ca_pem_written_to_box(self):
        pem = '-----BEGIN CERTIFICATE-----\nMIIBfake\n-----END CERTIFICATE-----'
        ud = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(proxy_ca_pem=pem))
        assert '/certs/mitmproxy-ca.pem' in ud                                       # written to the mounted CA dir
        assert '-----BEGIN CERTIFICATE-----' in ud                                   # the supplied CA, verbatim

    def test_no_ca_block_when_none(self):
        assert 'mitmproxy will self-generate' in self.ud                             # default: self-gen

    def test_env_override_shipped_verbatim(self):
        my_env = 'FASTAPI_API_KEY_VALUE=fromfile\nCACHE__SERVICE__BUCKET_NAME=my-bkt\nAWS_ACCESS_KEY_ID=AKIA\n'
        ud = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(), env_override=my_env,
            fastapi_api_key='GENERATED')                                            # generated value must be ignored
        assert 'FASTAPI_API_KEY_VALUE=fromfile' in ud                              # verbatim wins
        assert 'GENERATED' not in ud
        assert 'CACHE__SERVICE__BUCKET_NAME=my-bkt' in ud
        assert 'AWS_ACCESS_KEY_ID=AKIA' in ud

    def test_embeds_interceptor_files(self):
        assert f'{APP_DIR}/interceptors/active.py' in self.ud
        assert 'Content-Proxy interceptor loaded'  in self.ud                       # active.py body embedded
        assert 'def should_process_request'        in self.ud                       # logic module body embedded

    def test_shutdown_for_max_hours(self):
        assert 'shutdown -h +120' in self.ud                                        # 2h → 120 min

    def test_shutdown_for_fractional_hours(self):
        ud = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(max_hours=0.5))
        assert 'shutdown -h +30' in ud                                              # 0.5h → 30 min
        ud2 = Content_Proxy__User_Data__Builder().render(
            Schema__Content_Proxy__Create__Request(max_hours=1.5))
        assert 'shutdown -h +90' in ud2                                             # 1.5h → 90 min

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
