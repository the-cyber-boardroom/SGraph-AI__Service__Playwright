# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__HTTP__Probe
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.prometheus.service.Prometheus__HTTP__Base                     import Prometheus__HTTP__Base


class Prometheus__HTTP__Probe(Type_Safe):
    http : Prometheus__HTTP__Base

    def prometheus_ready(self, base_url: str, username: str = '', password: str = '') -> bool:
        url = f'{base_url.rstrip("/")}/-/healthy'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300

    def targets_status(self, base_url: str, username: str = '', password: str = '') -> dict:
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

    def query(self, base_url: str, query_str: str, username: str = '', password: str = '') -> dict:
        url = f'{base_url.rstrip("/")}/api/v1/query'
        try:
            resp = self.http.request('GET', url, params={'query': query_str},
                                     username=username, password=password)
        except Exception:
            return {}
        if resp.status_code != 200:
            return {}
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {}
