# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Session Schemas (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Lifetime                    import Enum__Session__Lifetime
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Close__Response         import Schema__Session__Close__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request         import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Response        import Schema__Session__Create__Response
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials             import Schema__Session__Credentials
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                    import Schema__Session__Info
from sgraph_ai_service_playwright.schemas.session.Schema__Session__State__Save__Request    import Schema__Session__State__Save__Request


class test_Schema__Session__Credentials(TestCase):

    def test__default_construct(self):
        creds = Schema__Session__Credentials()
        assert creds.cookies_vault_ref       is None
        assert creds.storage_state_vault_ref is None
        assert creds.extra_http_headers      == {}


class test_Schema__Session__Create__Request(TestCase):

    def test__defaults(self):
        req = Schema__Session__Create__Request()
        assert req.lifetime_hint == Enum__Session__Lifetime.EPHEMERAL
        assert req.lifetime_ms   == 300_000
        assert req.trace_id      is None
        assert req.credentials   is None

    def test__json_round_trip(self):
        req   = Schema__Session__Create__Request()
        clone = Schema__Session__Create__Request.from_json(req.json())
        assert clone.json() == req.json()


class test_Schema__Session__Info(TestCase):

    def test__default_construct(self):
        info = Schema__Session__Info()
        assert info.total_actions      == 0
        assert info.artefacts_captured == 0


class test_Schema__Session__Create__Response(TestCase):

    def test__default_construct(self):
        resp = Schema__Session__Create__Response()
        assert resp.session_info is not None
        assert resp.capabilities is not None


class test_Schema__Session__State__Save__Request(TestCase):

    def test__default_construct(self):
        req = Schema__Session__State__Save__Request()
        assert req.vault_ref is not None


class test_Schema__Session__Close__Response(TestCase):

    def test__default_construct(self):
        resp = Schema__Session__Close__Response()
        assert resp.artefacts         == []
        assert resp.total_duration_ms == 0
