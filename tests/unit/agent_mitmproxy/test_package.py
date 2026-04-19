# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy package scaffold (v0.1.32)
#
# Smoke-tests that the package is importable and the version + env-var + path
# constants load without side effects. Every downstream test relies on this
# passing first; if it breaks, fail early.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase


class test_agent_mitmproxy__scaffold(TestCase):

    def test__package_exposes_path(self):
        import agent_mitmproxy
        assert agent_mitmproxy.path.endswith('agent_mitmproxy')                      # Used by docker/Docker__Agent_Mitmproxy__Base.path_images()

    def test__version_constant_matches_file(self):
        from agent_mitmproxy.consts.version                                          import version__agent_mitmproxy
        assert str(version__agent_mitmproxy) == 'v0.1.32'

    def test__env_var_names(self):
        from agent_mitmproxy.consts                                                  import env_vars
        assert env_vars.ENV_VAR__PROXY_AUTH_USER == 'AGENT_MITMPROXY__PROXY_AUTH_USER'
        assert env_vars.ENV_VAR__PROXY_AUTH_PASS == 'AGENT_MITMPROXY__PROXY_AUTH_PASS'
        assert env_vars.ENV_VAR__API_KEY_NAME    == 'FAST_API__AUTH__API_KEY__NAME'    # Shared middleware convention with Playwright
        assert env_vars.ENV_VAR__API_KEY_VALUE   == 'FAST_API__AUTH__API_KEY__VALUE'

    def test__default_paths(self):
        from agent_mitmproxy.consts                                                  import paths
        assert paths.PATH__CA_CERT_PEM         == '/root/.mitmproxy/mitmproxy-ca-cert.pem'
        assert paths.PATH__CURRENT_INTERCEPTOR == '/app/current_interceptor.py'
