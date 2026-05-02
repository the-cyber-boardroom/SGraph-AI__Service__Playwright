# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__HTTP__Probe
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.vnc.service.Vnc__HTTP__Base                                   import Vnc__HTTP__Base


HEALTHZ_PATH       = '/healthz'
MITMWEB_FLOWS_PATH = '/mitmweb/flows'


class Vnc__HTTP__Probe(Type_Safe):
    http : Vnc__HTTP__Base

    def nginx_ready(self, base_url: str, username: str = '', password: str = '') -> bool:
        url = f'{base_url.rstrip("/")}{HEALTHZ_PATH}'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300

    def mitmweb_ready(self, base_url: str, username: str = '', password: str = '') -> bool:
        return self.nginx_ready(base_url, username=username, password=password)

    def flows_listing(self, base_url: str, username: str = '', password: str = '') -> List[dict]:
        url = f'{base_url.rstrip("/")}{MITMWEB_FLOWS_PATH}'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return []
        if resp.status_code != 200:
            return []
        try:
            body = resp.json()
        except (json.JSONDecodeError, ValueError):
            return []
        return body if isinstance(body, list) else []
