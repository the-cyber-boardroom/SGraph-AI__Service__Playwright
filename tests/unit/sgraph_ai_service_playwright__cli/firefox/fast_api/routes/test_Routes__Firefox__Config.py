# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Firefox__Config (TestClient, stub Firefox__Service)
# No mocks: a hand-rolled _FakeFirefoxService returns typed schemas.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                                                        import Fast_API

from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Health__State                import Enum__Health__State
from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Mitm__Mode                   import Enum__Mitm__Mode
from sgraph_ai_service_playwright__cli.firefox.fast_api.routes.Routes__Firefox__Config  import Routes__Firefox__Config
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Credentials__Info import Schema__Firefox__Credentials__Info
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Health           import Schema__Firefox__Health
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Mitm__Status     import Schema__Firefox__Mitm__Status
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Profile          import Schema__Firefox__Profile
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Security         import Schema__Firefox__Security
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Username             import Safe_Str__Username
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service                  import Firefox__Service
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime           import Safe_Str__ISO_Datetime


class _FakeFirefoxService(Firefox__Service):
    def get_credentials(self, region, stack_name):
        return Schema__Firefox__Credentials__Info(
            username        = Safe_Str__Username('admin')              ,
            last_rotated_at = Safe_Str__ISO_Datetime('2026-05-02T10:00:00Z'))

    def update_credentials(self, region, stack_name, request):
        pass

    def get_mitm_status(self, region, stack_name):
        return Schema__Firefox__Mitm__Status(
            enabled = True                         ,
            mode    = Enum__Mitm__Mode.INTERCEPT   )

    def get_mitm_url(self, region, stack_name):
        return 'http://1.2.3.4:8081'

    def get_security(self, region, stack_name):
        return Schema__Firefox__Security(
            self_signed_certs = True  ,
            ssl_intercept     = False )

    def update_security(self, region, stack_name, request):
        pass

    def get_profile(self, region, stack_name):
        return Schema__Firefox__Profile()

    def update_start_url(self, region, stack_name, url):
        pass

    def load_profile(self, region, stack_name, handle):
        pass

    def get_detailed_health(self, region, stack_name):
        return Schema__Firefox__Health(
            container_running = Enum__Health__State.GREEN ,
            firefox_process   = Enum__Health__State.GREEN ,
            mitm_proxy        = Enum__Health__State.GREEN ,
            network           = Enum__Health__State.GREEN ,
            login_page        = Enum__Health__State.GREEN ,
            overall           = Enum__Health__State.GREEN ,
            checked_at        = Safe_Str__ISO_Datetime('2026-05-02T10:00:00Z'))


def _client():
    svc = _FakeFirefoxService()
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Firefox__Config, service=svc)
    return app.client()


class test_Routes__Firefox__Config(TestCase):

    # ── credentials ─────────────────────────────────────────────────────────

    def test_get_credentials__200(self):
        resp = _client().get('/firefox/my-stack/credentials')
        assert resp.status_code == 200
        data = resp.json()
        assert data['username']        == 'admin'
        assert data['last_rotated_at'] == '2026-05-02T10:00:00Z'
        assert 'password' not in data                                               # never returned

    def test_update_credentials__200(self):
        resp = _client().put('/firefox/my-stack/credentials',
                             json={'username': 'bob', 'password': 'secret123'})
        assert resp.status_code == 200

    # ── MITM status ──────────────────────────────────────────────────────────

    def test_get_mitm_status__200(self):
        resp = _client().get('/firefox/my-stack/mitm/status')
        assert resp.status_code      == 200
        data = resp.json()
        assert data['enabled']       is True
        assert data['mode']          == 'intercept'

    def test_get_mitm_url__200(self):
        resp = _client().get('/firefox/my-stack/mitm/url')
        assert resp.status_code          == 200
        assert resp.json()['mitmweb_url'] == 'http://1.2.3.4:8081'

    # ── security ─────────────────────────────────────────────────────────────

    def test_get_security__200(self):
        resp = _client().get('/firefox/my-stack/security')
        assert resp.status_code == 200
        data = resp.json()
        assert data['self_signed_certs'] is True
        assert data['ssl_intercept']     is False

    def test_update_security__200(self):
        resp = _client().put('/firefox/my-stack/security',
                             json={'self_signed_certs': False, 'ssl_intercept': True})
        assert resp.status_code == 200

    # ── profile ──────────────────────────────────────────────────────────────

    def test_get_profile__200(self):
        resp = _client().get('/firefox/my-stack/profile')
        assert resp.status_code == 200
        data = resp.json()
        assert 'start_url'             in data
        assert 'loaded_profile_handle' in data

    def test_update_start_url__200(self):
        resp = _client().put('/firefox/my-stack/profile/start_url',
                             json={'url': 'https://example.com'})
        assert resp.status_code == 200

    def test_load_profile__200(self):
        resp = _client().put('/firefox/my-stack/profile/load',
                             json={'handle': 'profile'})
        assert resp.status_code == 200

    # ── detailed health ───────────────────────────────────────────────────────

    def test_get_health__200(self):
        resp = _client().get('/firefox/my-stack/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data['overall']           == 'green'
        assert data['container_running'] == 'green'
        assert data['firefox_process']   == 'green'
        assert data['mitm_proxy']        == 'green'
        assert 'checked_at'              in data

    def test_get_health__all_components_present(self):
        data = _client().get('/firefox/my-stack/health').json()
        for key in ('container_running', 'firefox_process', 'mitm_proxy',
                    'network', 'login_page', 'overall', 'checked_at'):
            assert key in data, f'missing key: {key}'
