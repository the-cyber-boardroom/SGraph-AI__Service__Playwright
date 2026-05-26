# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Mitmproxy__Capture__Client
#
# Thin HTTP client for the per-run capture endpoint
# (GET /capture/network-log/{run_id} on agent-mitmproxy). Returns the run's flows
# as a list of dicts — exactly the shape Journey__Assertion__Evaluator consumes.
# The HTTP call is exercised under the gated deploy tests; parse_ndjson is pure
# and unit-tested.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Value           import Safe_Str__Http__Header__Value
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url


class Mitmproxy__Capture__Client(Type_Safe):                                        # reads a run's captured flows
    base_url : Safe_Str__Url                   = None                               # e.g. http://agent-mitmproxy:8000
    api_key  : Safe_Str__Http__Header__Value   = None                               # X-API-Key value

    def network_log(self, run_id) -> List[dict]:
        import requests
        url      = f'{self.base_url}/capture/network-log/{run_id}'
        headers  = {'X-API-Key': str(self.api_key)} if self.api_key else {}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return self.parse_ndjson(response.text)

    def parse_ndjson(self, text: str) -> List[dict]:
        records = []
        for line in (text or '').splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records
