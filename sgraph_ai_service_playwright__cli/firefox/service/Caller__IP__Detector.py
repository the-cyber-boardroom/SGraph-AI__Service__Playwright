# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Caller__IP__Detector (firefox)
# Detects caller's public IP using AWS checkip service.
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address


DEFAULT_URL     = 'https://checkip.amazonaws.com'
DEFAULT_TIMEOUT = 10


class Caller__IP__Detector(Type_Safe):

    def detect(self) -> Safe_Str__IP__Address:
        resp = requests.get(DEFAULT_URL, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return Safe_Str__IP__Address(resp.text.strip())
