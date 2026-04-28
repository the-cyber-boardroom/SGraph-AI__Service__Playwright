# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Caller__IP__Detector (prometheus-local copy)
# Returns the caller's public IPv4 so Prometheus__Service can lock the
# per-stack SG ingress to a single /32. Mirrors the elastic + opensearch
# helpers. Future cleanup can promote a shared cli/aws/ version when 3+
# sections need it; for now each sister section is self-contained.
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address


DEFAULT_URL     = 'https://checkip.amazonaws.com'                                   # AWS-hosted, plain text response, no auth
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
        return Safe_Str__IP__Address(raw)                                           # Regex on the primitive rejects malformed responses
