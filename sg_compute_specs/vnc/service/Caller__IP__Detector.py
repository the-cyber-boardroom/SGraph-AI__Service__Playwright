# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Caller__IP__Detector
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sg_compute_specs.vnc.primitives.Safe_Str__IP__Address                          import Safe_Str__IP__Address


DEFAULT_URL     = 'https://checkip.amazonaws.com'
DEFAULT_TIMEOUT = 10


class Caller__IP__Detector(Type_Safe):
    url     : Safe_Str__Url = DEFAULT_URL
    timeout : int           = DEFAULT_TIMEOUT

    def fetch(self) -> str:                                                         # Override in tests to avoid real HTTP
        response = requests.get(str(self.url), timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def detect(self) -> Safe_Str__IP__Address:
        raw = self.fetch().strip()
        return Safe_Str__IP__Address(raw)
