# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__HTTP__Probe
# Read-only probe against a live Playwright stack. Single responsibility:
# checks that the Playwright FastAPI /health/status endpoint returns 2xx.
# Mirrors the pattern from Vnc__HTTP__Probe; simplified — one probe only.
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


HEALTH_PATH     = '/health/status'
DEFAULT_TIMEOUT = 10


class Playwright__HTTP__Probe(Type_Safe):
    timeout : int = DEFAULT_TIMEOUT

    def request(self, url: str) -> requests.Response:                            # Single seam — tests override
        return requests.get(url, timeout=self.timeout)

    def playwright_ready(self, base_url: str) -> bool:                           # True iff /health/status returns 2xx
        url = f'{base_url.rstrip("/")}{HEALTH_PATH}'
        try:
            resp = self.request(url)
        except Exception:
            return False
        return 200 <= resp.status_code < 300
