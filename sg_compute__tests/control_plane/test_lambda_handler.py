# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — control_plane/lambda_handler
# Smoke-tests that the handler module imports cleanly and _app resolves.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase


class test_lambda_handler(TestCase):

    def test_imports_cleanly(self):
        from sg_compute.control_plane import lambda_handler
        assert lambda_handler._app is not None

    def test_handler_is_mangum_or_none(self):
        from sg_compute.control_plane import lambda_handler
        if lambda_handler.handler is not None:
            assert callable(lambda_handler.handler)

    def test_app_has_routes(self):
        from sg_compute.control_plane import lambda_handler
        routes = [r.path for r in lambda_handler._app.routes]
        assert any('/api/health' in p for p in routes)
        assert any('/api/nodes'  in p for p in routes)
