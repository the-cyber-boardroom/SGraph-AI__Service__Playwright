# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.core.consts.env_vars
#
# Smoke-tests that every env var constant resolves to the expected string.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase

from sg_compute_specs.mitmproxy.core.consts                                          import env_vars


class test_env_vars(TestCase):

    def test__downstream_proxy_auth_vars(self):
        assert env_vars.ENV_VAR__PROXY_AUTH_USER == 'AGENT_MITMPROXY__PROXY_AUTH_USER'
        assert env_vars.ENV_VAR__PROXY_AUTH_PASS == 'AGENT_MITMPROXY__PROXY_AUTH_PASS'

    def test__upstream_forwarding_vars(self):
        assert env_vars.ENV_VAR__UPSTREAM_URL  == 'AGENT_MITMPROXY__UPSTREAM_URL'
        assert env_vars.ENV_VAR__UPSTREAM_USER == 'AGENT_MITMPROXY__UPSTREAM_USER'
        assert env_vars.ENV_VAR__UPSTREAM_PASS == 'AGENT_MITMPROXY__UPSTREAM_PASS'

    def test__filesystem_wiring_vars(self):
        assert env_vars.ENV_VAR__CA_CERT_PATH      == 'AGENT_MITMPROXY__CA_CERT_PATH'
        assert env_vars.ENV_VAR__INTERCEPTOR_PATH  == 'AGENT_MITMPROXY__INTERCEPTOR_PATH'

    def test__api_key_vars(self):
        assert env_vars.ENV_VAR__API_KEY_NAME  == 'FAST_API__AUTH__API_KEY__NAME'
        assert env_vars.ENV_VAR__API_KEY_VALUE == 'FAST_API__AUTH__API_KEY__VALUE'
