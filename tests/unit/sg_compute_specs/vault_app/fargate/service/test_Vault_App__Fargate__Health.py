# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Health
# Covers: wait_for happy path, timeout path, attempt counting, duration_ms,
# Authorization header injection.  Uses _http_get stub — no real HTTP.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Health   import Vault_App__Fargate__Health
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Health__Result  import Schema__VAF__Health__Result


class test_Vault_App__Fargate__Health(TestCase):

    _TEST_URL = 'https://18.130.45.12:443/info/health'

    def _make_health(self, timeout: int = 2, initial_delay: float = 0.0,
                     max_delay: float = 0.0, http_get=None):
        return Vault_App__Fargate__Health(
            timeout_seconds = timeout,
            initial_delay   = initial_delay,
            max_delay       = max_delay,
            _http_get       = http_get,
        )

    # ── happy path ───────────────────────────────────────────────────────────

    def test_wait_for_returns_ok_on_200(self):
        health = self._make_health(http_get=lambda url, hdrs: (200, True))
        result = health.wait_for(self._TEST_URL)
        assert result.ok is True

    def test_wait_for_status_code_200(self):
        health = self._make_health(http_get=lambda url, hdrs: (200, True))
        result = health.wait_for(self._TEST_URL)
        assert result.status_code == 200

    def test_wait_for_returns_schema_type(self):
        health = self._make_health(http_get=lambda url, hdrs: (200, True))
        result = health.wait_for(self._TEST_URL)
        assert isinstance(result, Schema__VAF__Health__Result)

    def test_wait_for_attempts_is_one_on_first_success(self):
        health = self._make_health(http_get=lambda url, hdrs: (200, True))
        result = health.wait_for(self._TEST_URL)
        assert result.attempts == 1

    def test_wait_for_url_recorded(self):
        health = self._make_health(http_get=lambda url, hdrs: (200, True))
        result = health.wait_for(self._TEST_URL)
        assert result.url == self._TEST_URL

    def test_wait_for_duration_ms_non_negative(self):
        health = self._make_health(http_get=lambda url, hdrs: (200, True))
        result = health.wait_for(self._TEST_URL)
        assert result.duration_ms >= 0

    def test_wait_for_succeeds_after_few_failures(self):
        calls = [0]
        def flaky(url, hdrs):
            calls[0] += 1
            if calls[0] < 3:
                return 503, False
            return 200, True
        health = self._make_health(timeout=5, initial_delay=0.0, http_get=flaky)
        result = health.wait_for(self._TEST_URL)
        assert result.ok is True
        assert result.attempts == 3

    # ── timeout path ─────────────────────────────────────────────────────────

    def test_wait_for_returns_not_ok_on_timeout(self):
        health = self._make_health(timeout=0, initial_delay=0.0,
                                   http_get=lambda url, hdrs: (503, False))
        result = health.wait_for(self._TEST_URL)
        assert result.ok is False

    def test_wait_for_attempts_counted_on_timeout(self):
        calls = [0]
        def always_fail(url, hdrs):
            calls[0] += 1
            return 503, False
        health = self._make_health(timeout=0, initial_delay=0.0, http_get=always_fail)
        result = health.wait_for(self._TEST_URL)
        assert result.attempts >= 1

    def test_wait_for_duration_ms_positive_on_timeout(self):
        health = self._make_health(timeout=0, initial_delay=0.0,
                                   http_get=lambda url, hdrs: (0, False))
        result = health.wait_for(self._TEST_URL)
        assert result.duration_ms >= 0

    # ── Authorization header ─────────────────────────────────────────────────

    def test_access_token_sent_as_bearer_header(self):
        captured = {}
        def capture_headers(url, hdrs):
            captured.update(hdrs)
            return 200, True
        health = self._make_health(http_get=capture_headers)
        health.wait_for(self._TEST_URL, access_token='sg_abc123')
        assert captured.get('Authorization') == 'Bearer sg_abc123'

    def test_no_auth_header_when_no_access_token(self):
        captured = {}
        def capture_headers(url, hdrs):
            captured.update(hdrs)
            return 200, True
        health = self._make_health(http_get=capture_headers)
        health.wait_for(self._TEST_URL, access_token='')
        assert 'Authorization' not in captured
