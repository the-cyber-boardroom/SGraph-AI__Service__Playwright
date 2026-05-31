# ═══════════════════════════════════════════════════════════════════════════════
# Live — /health/* smoke. Cheapest tests in the tier; run first as the
# implicit readiness check for the service container.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase


class test_health_endpoints(TestCase):

    def _client(self):                                                                   # Per-test grab so the conftest fixture/skip-gate still applies
        from tests.integration_live.conftest import _api_key, _api_key_header, _base_url
        import httpx
        return httpx.Client(base_url=_base_url(),
                            headers={_api_key_header(): _api_key()},
                            timeout=30.0)

    def test__info(self):
        with self._client() as c:
            r = c.get('/health/info')
            assert r.status_code == 200
            body = r.json()
            assert 'version' in body                                                     # Schema__Service__Info — shape only

    def test__status_reports_healthy(self):
        with self._client() as c:
            r = c.get('/health/status')
            assert r.status_code == 200
            body = r.json()
            assert body.get('healthy') is True                                           # If false, every other test will fail too — fail fast here

    def test__capabilities(self):
        with self._client() as c:
            r = c.get('/health/capabilities')
            assert r.status_code == 200
            body = r.json()
            assert 'detected_target' in body or 'capabilities' in body
