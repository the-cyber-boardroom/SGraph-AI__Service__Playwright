# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__HTTP__Probe
# Read-only probes against a live Prometheus instance. Single responsibility:
# probes that populate Schema__Prom__Health + the future `sp prom query`
# command. No mutations.
#
# Three probes (per plan 5):
#   - prometheus_ready(base_url)         — GET /-/healthy            → bool
#   - targets_status(base_url)           — GET /api/v1/targets       → dict
#   - query(base_url, query_str)         — GET /api/v1/query?query=… → dict
#
# All probes return False / {} on any failure; caller maps to '-1' sentinels
# in Schema__Prom__Health.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Base    import Prometheus__HTTP__Base


class Prometheus__HTTP__Probe(Type_Safe):
    http : Prometheus__HTTP__Base                                                   # Composed; tests override http.request

    def prometheus_ready(self, base_url: str, username: str = '', password: str = '') -> bool:    # True iff /-/healthy returns 2xx
        url = f'{base_url.rstrip("/")}/-/healthy'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300

    def targets_status(self, base_url: str, username: str = '', password: str = '') -> dict:     # Returns {} when unreachable — caller derives targets_total / targets_up from data.activeTargets
        url = f'{base_url.rstrip("/")}/api/v1/targets'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return {}
        if resp.status_code != 200:
            return {}
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {}

    def query(self, base_url: str, query_str: str, username: str = '', password: str = '') -> dict:  # Forwarded for future `sp prom query` — empty dict on failure
        url = f'{base_url.rstrip("/")}/api/v1/query'
        try:
            resp = self.http.request('GET', url, params={'query': query_str}, username=username, password=password)
        except Exception:
            return {}
        if resp.status_code != 200:
            return {}
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {}
