# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Docker__Runtime (Target C plumbing)
# The build-context test needs no docker — it asserts the engine is materialised
# (BANNED_IPS inlined) and the server + Dockerfile are copied into the context.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil

from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Runtime import Sentinel__Docker__Runtime, docker_available


class TestConfig:
    def test_base_url_uses_configured_port(self):
        assert Sentinel__Docker__Runtime(port=9001).base_url() == 'http://127.0.0.1:9001'

    def test_docker_available_returns_bool(self):
        assert isinstance(docker_available(), bool)


class TestBuildContext:
    def test_context_has_materialised_engine_and_assets(self):
        ctx = Sentinel__Docker__Runtime().build_context()
        try:
            engine = os.path.join(ctx, 'sentinel_l1.js')
            assert os.path.exists(engine)
            with open(engine) as fh:
                src = fh.read()
            assert 'var BANNED_IPS = [];' not in src                                # inlined
            assert '10.0.0.6' in src                                                # banned-ip fixture present
            assert os.path.exists(os.path.join(ctx, 'server.node.js'))
            assert os.path.exists(os.path.join(ctx, 'Dockerfile'))
        finally:
            shutil.rmtree(ctx, ignore_errors=True)
