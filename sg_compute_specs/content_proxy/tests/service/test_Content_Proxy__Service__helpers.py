# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Service pure helpers (sg_rules / derive_fqdn)
# No AWS — just the firewall + hostname-derivation logic for the --edge/--with-aws-dns path.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                   import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                    import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request   import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.service.Content_Proxy__Service                    import (sg_rules, derive_fqdn,
                                                                                            EXT_PROXY_PORT, VAULT_PORT, ACME_PORT)


class test_sg_rules(TestCase):

    def test_none_opens_proxy_and_vault_to_caller_only(self):
        inbound, extra = sg_rules(Enum__Content_Proxy__Tls.NONE)
        assert inbound == [EXT_PROXY_PORT, VAULT_PORT]
        assert extra == {}                                                            # nothing world-open

    def test_letsencrypt_opens_acme_to_world(self):
        inbound, extra = sg_rules(Enum__Content_Proxy__Tls.LETSENCRYPT)
        assert extra == {ACME_PORT: '0.0.0.0/0'}                                      # http-01 validated by LE, not the caller

    def test_caddy_hostname_opens_443_and_80_to_world(self):
        inbound, extra = sg_rules(Enum__Content_Proxy__Tls.NONE,
                                  Enum__Content_Proxy__Edge.CADDY, 'h.sg-compute.sgraph.ai')
        assert extra[VAULT_PORT] == '0.0.0.0/0'                                       # Claude must reach :443
        assert extra[ACME_PORT]  == '0.0.0.0/0'                                       # Caddy ACME http-01

    def test_caddy_without_hostname_stays_caller_scoped(self):
        inbound, extra = sg_rules(Enum__Content_Proxy__Tls.NONE, Enum__Content_Proxy__Edge.CADDY, '')
        assert extra == {}                                                            # internal CA / local — no world-open


class test_derive_fqdn(TestCase):

    def test_explicit_hostname_wins(self):
        req = Schema__Content_Proxy__Create__Request(hostname='custom.example.com', with_aws_dns=True)
        assert derive_fqdn('keen-darwin', req) == 'custom.example.com'

    def test_with_aws_dns_derives_from_stack_and_zone(self):
        req = Schema__Content_Proxy__Create__Request(with_aws_dns=True)
        assert derive_fqdn('keen-darwin', req) == 'keen-darwin.sg-compute.sgraph.ai'

    def test_neither_returns_blank(self):
        req = Schema__Content_Proxy__Create__Request()
        assert derive_fqdn('keen-darwin', req) == ''

    def test_zone_override_via_env(self):
        os.environ['SG_AWS__DNS__DEFAULT_ZONE'] = 'alt.zone.test'
        try:
            req = Schema__Content_Proxy__Create__Request(with_aws_dns=True)
            assert derive_fqdn('keen-darwin', req) == 'keen-darwin.alt.zone.test'
        finally:
            del os.environ['SG_AWS__DNS__DEFAULT_ZONE']
