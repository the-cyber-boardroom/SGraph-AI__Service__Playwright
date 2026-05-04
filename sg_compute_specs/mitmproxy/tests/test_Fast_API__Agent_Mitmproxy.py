# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.api.Fast_API__Agent_Mitmproxy
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase

from sg_compute_specs.mitmproxy.api.Fast_API__Agent_Mitmproxy                        import Fast_API__Agent_Mitmproxy


class test_Fast_API__Agent_Mitmproxy(TestCase):

    def test__config_enables_api_key(self):
        fast_api = Fast_API__Agent_Mitmproxy()
        assert fast_api.config.enable_api_key is True                                # Middleware rejects un-authenticated calls

    def test__setup_registers_health_routes(self):
        fast_api = Fast_API__Agent_Mitmproxy().setup()
        route_paths = [str(getattr(r, 'path', '')) for r in fast_api.app().routes]
        assert '/health/info'   in route_paths
        assert '/health/status' in route_paths
