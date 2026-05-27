# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__Reverse_Proxy
# parse_routes() is pure logic; mount() registration is asserted against a real
# FastAPI app (no mocks). End-to-end forwarding is validated on a live stack via
# the SSM procedure in the tech spec (needs a real upstream).
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest

from sg_compute.fast_api.reverse_proxy.Fast_API__Reverse_Proxy import (Fast_API__Reverse_Proxy,
                                                                       ENV_VAR__ROUTES         )


class TestFast_API__Reverse_Proxy:

    def setup_method(self):
        os.environ.pop(ENV_VAR__ROUTES, None)

    def teardown_method(self):
        os.environ.pop(ENV_VAR__ROUTES, None)

    # ── parse_routes ─────────────────────────────────────────────────────────

    def test_parse_routes__empty_when_unset(self):
        assert Fast_API__Reverse_Proxy().parse_routes() == {}

    def test_parse_routes__single(self):
        os.environ[ENV_VAR__ROUTES] = 'pw=http://sg-playwright:8000'
        assert Fast_API__Reverse_Proxy().parse_routes() == {'pw': 'http://sg-playwright:8000'}

    def test_parse_routes__multiple(self):
        os.environ[ENV_VAR__ROUTES] = 'pw=http://sg-playwright:8000,mitm=http://agent-mitmproxy:8081'
        assert Fast_API__Reverse_Proxy().parse_routes() == {'pw'  : 'http://sg-playwright:8000'  ,
                                                            'mitm': 'http://agent-mitmproxy:8081'}

    def test_parse_routes__strips_slashes_and_whitespace(self):
        os.environ[ENV_VAR__ROUTES] = '  /pw/ = http://sg-playwright:8000/  '
        assert Fast_API__Reverse_Proxy().parse_routes() == {'pw': 'http://sg-playwright:8000'}

    def test_parse_routes__skips_malformed_entries(self):
        os.environ[ENV_VAR__ROUTES] = 'pw=http://sg-playwright:8000,,garbage,=nope,empty='
        assert Fast_API__Reverse_Proxy().parse_routes() == {'pw': 'http://sg-playwright:8000'}

    # ── mount registration ───────────────────────────────────────────────────

    def test_mount__no_op_when_unset(self):
        from fastapi import FastAPI
        app    = FastAPI()
        before = {r.path for r in app.routes}
        routes = Fast_API__Reverse_Proxy().mount(app)
        assert routes == {}
        assert {r.path for r in app.routes} == before                              # nothing added

    def test_mount__registers_prefix_and_catch_all(self):
        from fastapi import FastAPI
        os.environ[ENV_VAR__ROUTES] = 'pw=http://sg-playwright:8000'
        app    = FastAPI()
        routes = Fast_API__Reverse_Proxy().mount(app)
        assert routes == {'pw': 'http://sg-playwright:8000'}
        paths = {r.path for r in app.routes}
        assert '/pw/'            in paths
        assert '/pw/{path:path}' in paths

    def test_mount__all_methods_on_catch_all(self):
        from fastapi import FastAPI
        os.environ[ENV_VAR__ROUTES] = 'pw=http://sg-playwright:8000'
        app = FastAPI()
        Fast_API__Reverse_Proxy().mount(app)
        catch_all = next(r for r in app.routes if getattr(r, 'path', '') == '/pw/{path:path}')
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH'):
            assert verb in catch_all.methods

    def test_mount__multiple_prefixes(self):
        from fastapi import FastAPI
        os.environ[ENV_VAR__ROUTES] = 'pw=http://sg-playwright:8000,mitm=http://agent-mitmproxy:8081'
        app = FastAPI()
        Fast_API__Reverse_Proxy().mount(app)
        paths = {r.path for r in app.routes}
        assert '/pw/{path:path}'   in paths
        assert '/mitm/{path:path}' in paths
