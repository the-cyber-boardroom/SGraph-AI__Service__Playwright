# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Action + Error Schemas (spec §5.9 + §5.10)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request         import Schema__Action__Request
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Response        import Schema__Action__Response
from sgraph_ai_service_playwright.schemas.core.Schema__Error__Response         import Schema__Error__Response


class test_Schema__Action__Request(TestCase):

    def test__default_construct(self):
        req = Schema__Action__Request()
        assert req.step           == {}
        assert req.capture_config is None
        assert req.trace_id       is None


class test_Schema__Action__Response(TestCase):

    def test__default_construct(self):
        resp = Schema__Action__Response()
        assert resp.step_result  is not None
        assert resp.session_info is not None


class test_Schema__Error__Response(TestCase):

    def test__round_trip(self):
        err   = Schema__Error__Response(error_code='test_err', error_message='boom')
        clone = Schema__Error__Response.from_json(err.json())
        assert str(clone.error_code)    == 'test_err'
        assert str(clone.error_message) == 'boom'
        assert clone.capabilities       is None

    def test__capabilities_surfaced(self):
        from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities import Schema__Service__Capabilities
        caps = Schema__Service__Capabilities()
        err  = Schema__Error__Response(error_code='sink_incompatible_with_deployment',
                                       error_message='Lambda cannot LOCAL_FILE',
                                       capabilities=caps)
        assert err.capabilities is caps
