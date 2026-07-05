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
            fastapi_api_key='FK123', access_token='AT456', region='eu-west-2',
            aws_creds={'AWS_ACCESS_KEY_ID': 'AKIA', 'AWS_SECRET_ACCESS_KEY': 'sk'})
        assert 'FASTAPI_API_KEY_VALUE=FK123'           in ud
        assert 'FAST_API__AUTH__API_KEY__VALUE=AT456'  in ud                          # access token = playwright + vault key
        assert 'SGRAPH_SEND__ACCESS_TOKEN=AT456'       in ud
        assert 'AWS_DEFAULT_REGION=eu-west-2'       in ud
        assert 'CACHE__SERVICE__BUCKET_NAME=my-scripts' in ud
        assert 'AWS_ACCESS_KEY_ID=AKIA'             in ud                            # forwarded creds (parity path)
        assert 'AWS_SECRET_ACCESS_KEY=sk'           in ud

    def test_no_aws_creds_baked_by_default(self):
        # the .env body (not the embedded compose, which now interpolates ${AWS_*}) must carry no creds
        env = Content_Proxy__User_Data__Builder().render_env(
            Schema__Content_Proxy__Create__Request(), region='eu-west-2')            # no aws_creds → instance role
        assert 'AWS_ACCESS_KEY_ID='   not in env
        assert 'AWS_SECRET_ACCESS_KEY=' not in env

    def test_account_id_set_on_instance_role_path(self):
        env = Content_Proxy__User_Data__Builder().render_env(
            Schema__Content_Proxy__Create__Request(), region='eu-west-2', account_id='504558652080')  # no creds forwarded
        assert 'AWS_ACCOUNT_ID=504558652080' in env                                  # set even without --forward-aws-creds (the app reads it; creds still come from IMDS)
        assert 'AWS_ACCESS_KEY_ID='   not in env                                     # still no baked creds

    def test_account_id_not_duplicated_when_also_forwarded(self):
        env = Content_Proxy__User_Data__Builder().render_env(
            Schema__Content_Proxy__Create__Request(), region='eu-west-2', account_id='111122223333',
            aws_creds={'AWS_ACCOUNT_ID': '111122223333', 'AWS_ACCESS_KEY_ID': 'AKIA'})
        assert env.count('AWS_ACCOUNT_ID=111122223333') == 1                         # written once (explicit), not again from aws_creds
        assert 'AWS_ACCESS_KEY_ID=AKIA' in env

    def test_account_id_omitted_when_blank(self):
        env = Content_Proxy__User_Data__Builder().render_env(
            Schema__Content_Proxy__Create__Request(), region='eu-west-2')            # account_id defaults to ''
        assert 'AWS_ACCOUNT_ID=' not in env                                          # no empty line that would shadow IMDS-derived account

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

    def test_writes_pw_override(self):
        assert '/opt/content-proxy/overrides/serve_with_proxy.py'        in self.ud   # /pw entrypoint override written
        assert '/opt/content-proxy/overrides/Fast_API__Reverse_Proxy.py' in self.ud
        assert 'sg_overrides' in self.ud

    def test_none_edge_writes_no_caddyfile(self):
        assert 'edge=none — vault is the front door' in self.ud                       # default: no Caddyfile
        assert f'{APP_DIR}/Caddyfile' not in self.ud

    def test_caddy_edge_writes_caddyfile_and_drops_pw_override(self):
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge import Enum__Content_Proxy__Edge
        req = Schema__Content_Proxy__Create__Request(edge=Enum__Content_Proxy__Edge.CADDY)
        ud  = Content_Proxy__User_Data__Builder().render(req)                         # internal (no hostname) caddy edge
        assert f'{APP_DIR}/Caddyfile' in ud                                           # the edge Caddyfile is written
        assert 'localhost, 127.0.0.1 {' in ud                                         # internal named site
        assert 'cp-caddy' in ud                                                       # compose has the caddy service
        assert 'serve_with_proxy' not in ud                                          # vault is a plain origin — no /pw patch
        assert 'edge=caddy — /pw routed at the edge' in ud

    def test_caddy_edge_hostname_writes_fqdn_site(self):
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge import Enum__Content_Proxy__Edge
        req = Schema__Content_Proxy__Create__Request(edge=Enum__Content_Proxy__Edge.CADDY)
        ud  = Content_Proxy__User_Data__Builder().render(req, hostname='h.sg-compute.sgraph.ai')
        assert 'h.sg-compute.sgraph.ai {' in ud                                       # FQDN site → Caddy auto-ACME
        assert '"80:80"' in ud                                                        # ACME http-01 port published

    def test_no_firefox_block_by_default(self):
        assert 'no interactive browsers (--firefox 0)' in self.ud                     # default: fleet disabled
        assert 'cp-firefox' not in self.ud

    def test_firefox_count_wires_proxy_ca_and_certutil(self):
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge import Enum__Content_Proxy__Edge
        req = Schema__Content_Proxy__Create__Request(edge=Enum__Content_Proxy__Edge.CADDY)
        ud  = Content_Proxy__User_Data__Builder().render(req, firefox_count=2)
        assert 'cp-firefox-1:' in ud and 'cp-firefox-2:' in ud                        # compose fleet embedded
        assert 'dnf install -y nss-tools' in ud                                       # certutil dependency
        assert '/opt/content-proxy/certs/mitmproxy-ca-cert.pem' in ud                 # mitmproxy self-gen CA (not --ca-from-local)
        assert ud.count('certutil -A -n "mitmproxy CA" -t "TCu,,"') == 2              # one CA install per profile
        assert '/opt/content-proxy/firefox/1/profile' in ud                           # per-container profile dir
        assert 'network.proxy.http",          "mitmproxy-int"' in ud                  # user.js proxy → internal proxy host
        assert 'network.proxy.http_port",     8080' in ud
        assert 'handle_path /browser/firefox/1/*' in ud                               # caddy edge routes written too
        assert 'restart cp-firefox-2' in ud                                           # reload after profile prep

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('log_file', 'app_dir', 'env_body', 'compose_body',
                                'active_body', 'logic_body', 'ca_block', 'overrides_block',
                                'caddy_block', 'firefox_block', 'shutdown_line')
