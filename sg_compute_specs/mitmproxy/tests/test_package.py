# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy package scaffold
#
# Smoke-tests that the package is importable and the version + env-var + path
# constants load without side effects.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase


class test_mitmproxy__scaffold(TestCase):

    def test__package_exposes_path(self):
        import sg_compute_specs.mitmproxy as _pkg
        assert _pkg.path.endswith('mitmproxy')                                       # Used by docker/Docker__Agent_Mitmproxy__Base.path_images()

    def test__version_constant_matches_file(self):
        from sg_compute_specs.mitmproxy.core.consts.version                          import version__agent_mitmproxy
        assert str(version__agent_mitmproxy) == 'v0.1.33'

    def test__env_var_names(self):
        from sg_compute_specs.mitmproxy.core.consts                                  import env_vars
        assert env_vars.ENV_VAR__PROXY_AUTH_USER == 'AGENT_MITMPROXY__PROXY_AUTH_USER'
        assert env_vars.ENV_VAR__PROXY_AUTH_PASS == 'AGENT_MITMPROXY__PROXY_AUTH_PASS'
        assert env_vars.ENV_VAR__API_KEY_NAME    == 'FAST_API__AUTH__API_KEY__NAME'
        assert env_vars.ENV_VAR__API_KEY_VALUE   == 'FAST_API__AUTH__API_KEY__VALUE'

    def test__default_paths(self):
        from sg_compute_specs.mitmproxy.core.consts                                  import paths
        assert paths.PATH__CA_CERT_PEM         == '/root/.mitmproxy/mitmproxy-ca-cert.pem'
        assert paths.PATH__CURRENT_INTERCEPTOR == '/app/current_interceptor.py'
