# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__HTTP__Probe
# Read-only probes against a live VNC stack. Single responsibility: probes
# that populate Schema__Vnc__Health + the future `sp vnc flows` command.
#
# Three probes:
#   - nginx_ready(base_url)       — GET /          → bool  (nginx terminator)
#   - mitmweb_ready(base_url)     — GET /flows     → bool  (mitmweb reachable)
#   - flows_listing(base_url)     — GET /flows     → list  (mitmweb flows JSON)
#
# All probes return False / [] / {} on any failure; caller maps to
# Schema__Vnc__Health '-1' sentinel for flow_count when listing fails.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Base                  import Vnc__HTTP__Base


MITMWEB_FLOWS_PATH = '/flows'                                                       # mitmweb flow listing endpoint (GET) — the path is /flows, NOT /api/flows; mitmweb has no /api/ prefix


class Vnc__HTTP__Probe(Type_Safe):
    http : Vnc__HTTP__Base                                                          # Composed; tests override http.request

    def nginx_ready(self, base_url: str, username: str = '', password: str = '') -> bool:    # True iff nginx '/' returns 2xx
        url = base_url.rstrip('/') + '/'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300

    def mitmweb_ready(self, base_url: str, username: str = '', password: str = '') -> bool:  # True iff mitmweb /flows returns 200
        url = f'{base_url.rstrip("/")}{MITMWEB_FLOWS_PATH}'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return resp.status_code == 200

    def flows_listing(self, base_url: str, username: str = '', password: str = '') -> List[dict]:  # Parsed flow listing; empty list on any failure
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
        return body if isinstance(body, list) else []                               # mitmweb returns a top-level array; defensive
