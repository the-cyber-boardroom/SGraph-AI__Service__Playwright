# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: CLI renderer tests (capture console output)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest      import TestCase

from rich.console  import Console

from sg_compute_specs.content_proxy.cli.Renderers                                   import render_create, render_info
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                  import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Response import Schema__Content_Proxy__Create__Response
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info      import Schema__Content_Proxy__Stack__Info


def _cap(fn, *args):
    c = Console(highlight=False, width=200, force_terminal=False)
    with c.capture() as cap:
        fn(*args, c)
    return cap.get()


class test_render_info(TestCase):

    def test_info_shows_proxy_vault_pw_and_helpers(self):
        info = Schema__Content_Proxy__Stack__Info(stack_name='cp-demo', public_ip='35.179.109.135',
                                                 region='eu-west-2', tls=Enum__Content_Proxy__Tls.NONE)
        out  = _cap(render_info, info)
        assert 'cp-demo' in out
        assert 'http://35.179.109.135:8080'  in out                                 # Mode-1 proxy endpoint
        assert 'http://35.179.109.135:443/'  in out                                 # vault (plain HTTP behind 443, NONE)
        assert '/pw/' in out                                                        # sg-playwright via /pw
        assert 'sg content-proxy smoke' in out                                      # verify hint
        assert 'local ca' in out                                                    # CA import hint

    def test_info_https_when_tls(self):
        info = Schema__Content_Proxy__Stack__Info(public_ip='1.2.3.4', tls=Enum__Content_Proxy__Tls.LETSENCRYPT)
        out  = _cap(render_info, info)
        assert 'https://1.2.3.4/' in out


class test_render_create(TestCase):

    def test_create_surfaces_generated_secrets_once(self):
        info = Schema__Content_Proxy__Stack__Info(stack_name='cp-demo', instance_id='i-0123456789abcdef0')
        resp = Schema__Content_Proxy__Create__Response(stack_info=info, fastapi_api_key='FK',
                                                      playwright_api_key='PK', elapsed_ms=3200)
        out  = _cap(render_create, resp)
        assert 'cp-demo' in out and 'Launching' in out
        assert 'FK' in out and 'PK' in out                                          # secrets shown once
        assert 'generated secrets' in out                                           # generated (no env-file)

    def test_create_labels_env_file_secrets(self):
        info = Schema__Content_Proxy__Stack__Info(stack_name='cp-demo')
        resp = Schema__Content_Proxy__Create__Response(stack_info=info, fastapi_api_key='FK',
                                                      playwright_api_key='PK', secrets_from_env=True)
        out  = _cap(render_create, resp)
        assert 'from --env-file' in out and 'generated secrets' not in out          # reused, not generated
