# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: OpenSearch__HTTP__Probe
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.opensearch.service.OpenSearch__HTTP__Base                     import OpenSearch__HTTP__Base


class OpenSearch__HTTP__Probe(Type_Safe):
    http : OpenSearch__HTTP__Base

    def cluster_health(self, base_url: str, username: str = '', password: str = '') -> dict:
        url = f'{base_url.rstrip("/")}/_cluster/health'
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

    def dashboards_ready(self, base_url: str, username: str = '', password: str = '') -> bool:
        url = base_url.rstrip('/') + '/'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300
