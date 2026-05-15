# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__Playwright__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.schemas.Schema__Playwright__Create__Request import Schema__Playwright__Create__Request


class TestSchemaPlaywrightCreateRequest:

    def test_defaults(self):
        req = Schema__Playwright__Create__Request()
        assert req.region            == 'eu-west-2'
        assert req.instance_type     == 't3.medium'
        assert req.from_ami          == ''
        assert req.stack_name        == ''
        assert req.caller_ip         == ''
        assert req.max_hours         == 1.0
        assert req.with_mitmproxy    is False
        assert req.intercept_script  == ''
        assert req.image_tag         == 'latest'
        assert req.api_key           == ''
        assert int(req.disk_size_gb) == 20
        assert req.use_spot          is True

    def test_override_with_mitmproxy(self):
        req = Schema__Playwright__Create__Request()
        req.with_mitmproxy = True
        assert req.with_mitmproxy is True

    def test_override_intercept_script(self):
        req = Schema__Playwright__Create__Request()
        req.intercept_script = 'def request(flow):\n    pass'
        assert 'def request' in req.intercept_script

    def test_override_use_spot_false(self):
        req = Schema__Playwright__Create__Request()
        req.use_spot = False
        assert req.use_spot is False
