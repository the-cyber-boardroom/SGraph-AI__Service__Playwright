# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — control_plane/lambda_handler
# Smoke-tests that the handler module imports cleanly and _app resolves.
# lambda_handler runs Fast_API__Compute().setup() at import time, which now
# requires FAST_API__AUTH__API_KEY__VALUE to be set (T1.6 boot assertion).
# setUpModule/tearDownModule bracket all tests so the env var is present when
# the module is first imported and module cache stays consistent.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
import os
import sys
from unittest                                                                  import TestCase

_TEST_API_KEY = 'test-api-key-lambda-1234567890'                               # ≥ 16 chars; not a real key
_MODULE_PATH  = 'sg_compute.control_plane.lambda_handler'


def setUpModule():
    os.environ['FAST_API__AUTH__API_KEY__VALUE'] = _TEST_API_KEY
    os.environ['FAST_API__AUTH__API_KEY__NAME']  = 'X-API-Key'
    sys.modules.pop(_MODULE_PATH, None)                                        # evict stale cache so import re-runs


def tearDownModule():
    os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)
    os.environ.pop('FAST_API__AUTH__API_KEY__NAME' , None)
    sys.modules.pop(_MODULE_PATH, None)                                        # clean up after ourselves


class test_lambda_handler(TestCase):

    def test_imports_cleanly(self):
        from sg_compute.control_plane import lambda_handler
        assert lambda_handler._app is not None

    def test_run_is_callable(self):
        from sg_compute.control_plane import lambda_handler
        assert callable(lambda_handler.run)

    def test_no_mangum_import(self):
        import inspect
        from sg_compute.control_plane import lambda_handler
        src = inspect.getsource(lambda_handler)
        assert 'mangum' not in src.lower()

    def test_app_has_routes(self):
        from sg_compute.control_plane import lambda_handler
        routes = [r.path for r in lambda_handler._app.routes]
        assert any('/api/health' in p for p in routes)
        assert any('/api/nodes'  in p for p in routes)
