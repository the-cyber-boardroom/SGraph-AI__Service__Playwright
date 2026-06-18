# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: schema round-trip tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode                  import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy                 import Enum__Content_Proxy__Proxy
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Vault__Kind           import Enum__Content_Proxy__Vault__Kind
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request   import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Flow__Summary     import Schema__Content_Proxy__Flow__Summary
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Vault__Source     import Schema__Content_Proxy__Vault__Source


class test_schemas(TestCase):

    def test_create_request_defaults(self):
        req = Schema__Content_Proxy__Create__Request()
        assert req.mode               == Enum__Content_Proxy__Mode.DIRECT_PROXY
        assert req.tls                == Enum__Content_Proxy__Tls.NONE
        assert str(req.mitmproxy_image) == 'mitmproxy/mitmproxy:12.2.3'
        assert str(req.playwright_image)   == 'diniscruz/sg-playwright'
        assert str(req.vault_app_image)    == 'diniscruz/sg-send-vault'
        assert str(req.mitm_service_image) == 'diniscruz/mgraph-ai-service-mitmproxy'
        assert list(req.vaults_to_load) == []                                       # MVP: no vaults

    def test_create_request_round_trip(self):
        req  = Schema__Content_Proxy__Create__Request(mode = Enum__Content_Proxy__Mode.VAULT_WEB,
                                                      tls  = Enum__Content_Proxy__Tls.LETSENCRYPT)
        req2 = Schema__Content_Proxy__Create__Request.from_json(req.json())
        assert req2.json() == req.json()
        assert req2.mode == Enum__Content_Proxy__Mode.VAULT_WEB
        assert req2.tls  == Enum__Content_Proxy__Tls.LETSENCRYPT

    def test_vault_source(self):
        v = Schema__Content_Proxy__Vault__Source(kind=Enum__Content_Proxy__Vault__Kind.SGIT,
                                                 ref='s3://bkt/logs', target='logs')
        assert v.kind == Enum__Content_Proxy__Vault__Kind.SGIT
        assert str(v.ref) == 's3://bkt/logs'

    def test_flow_summary(self):
        f = Schema__Content_Proxy__Flow__Summary(via=Enum__Content_Proxy__Proxy.EXT,
                                                 method='GET', host='news.site', path='/9',
                                                 status_code=200,
                                                 action=Enum__Content_Proxy__Flow__Action.INJECTED,
                                                 fastapi_connected=True)
        assert f.action == Enum__Content_Proxy__Flow__Action.INJECTED
        assert f.via    == Enum__Content_Proxy__Proxy.EXT

    def test_stack_info_defaults(self):
        info = Schema__Content_Proxy__Stack__Info()
        assert info.mitmproxy_ext_ok is False
        assert info.vaults_present   == []
