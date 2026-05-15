# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Stack__Mapper
# Pure dict-in / schema-out: verifies that the TLS / AccessToken tags surface on
# Schema__Vault_App__Info and that vault_url switches scheme based on StackTLS.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper import Vault_App__Stack__Mapper


def _instance(tags: dict, public_ip: str = '13.40.11.113') -> dict:
    return {
        'InstanceId'     : 'i-abc'                                                 ,
        'InstanceType'   : 't3.medium'                                             ,
        'ImageId'        : 'ami-xyz'                                               ,
        'State'          : {'Name': 'running'}                                     ,
        'PublicIpAddress': public_ip                                               ,
        'SecurityGroups' : [{'GroupId': 'sg-1'}]                                   ,
        'Tags'           : [{'Key': k, 'Value': v} for k, v in tags.items()]       ,
    }


class TestVaultAppStackMapper:

    def test_tls_on_yields_https_vault_url(self):
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName': 's', 'StackTLS': 'true'}), 'eu-west-2')
        assert info.tls_enabled is True
        assert info.vault_url   == 'https://13.40.11.113'

    def test_tls_off_falls_back_to_plain_http_on_8080(self):
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName': 's'}), 'eu-west-2')              # no StackTLS tag
        assert info.tls_enabled is False
        assert info.vault_url   == 'http://13.40.11.113:8080'

    def test_access_token_surfaces_from_tag(self):
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName': 's', 'AccessToken': 'tok-123'}), 'eu-west-2')
        assert info.access_token == 'tok-123'

    def test_no_public_ip_yields_empty_vault_url(self):
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName': 's', 'StackTLS': 'true'}, public_ip=''), 'eu-west-2')
        assert info.vault_url      == ''
        assert info.playwright_url == ''

    def test_with_playwright_yields_external_playwright_url(self):
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName': 's', 'StackWithPlaywright': 'true'}), 'eu-west-2')
        assert info.with_playwright is True
        assert info.playwright_url  == 'http://13.40.11.113'         # port 80 — default HTTP; suffix omitted for cleanliness

    def test_without_playwright_omits_playwright_url(self):
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName': 's'}), 'eu-west-2')              # no StackWithPlaywright
        assert info.with_playwright is False
        assert info.playwright_url  == ''

    def test_tls_hostname_tag_drives_https_vault_url_to_the_fqdn(self):
        # Cert is for the FQDN — the vault_url MUST match the cert SAN or browsers / egress
        # proxies reject. The mapper must surface the FQDN, not the IP, when the tag is set.
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName'       : 's'                            ,
                       'StackTLS'        : 'true'                         ,
                       'StackTlsHostname': 'test-2.sg-compute.sgraph.ai'  }),
            'eu-west-2')
        assert info.vault_url == 'https://test-2.sg-compute.sgraph.ai'   # FQDN, not the IP

    def test_tls_hostname_tag_drives_playwright_url_to_the_fqdn(self):
        # Same FQDN works for plain-HTTP playwright too (no cert involved, but a single
        # host for vault + playwright is friendlier for callers).
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName'          : 's'                            ,
                       'StackTLS'           : 'true'                         ,
                       'StackTlsHostname'   : 'test-2.sg-compute.sgraph.ai'  ,
                       'StackWithPlaywright': 'true'                         }),
            'eu-west-2')
        assert info.playwright_url == 'http://test-2.sg-compute.sgraph.ai'

    def test_no_tls_with_fqdn_yields_plain_http_vault_url_on_8080(self):
        # --no-with-tls-check + --with-aws-dns: vault binds plain HTTP on :8080,
        # SG opens it world-open, URL uses the FQDN (which the user-supplied or
        # auto-derived A record points at this stack's IP).
        info = Vault_App__Stack__Mapper().to_info(
            _instance({'StackName'       : 's'                              ,
                       'StackTlsHostname': 'plain-stack.sg-compute.sgraph.ai'}),  # no StackTLS tag = TLS off
            'eu-west-2')
        assert info.tls_enabled is False
        assert info.vault_url   == 'http://plain-stack.sg-compute.sgraph.ai:8080'
