# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Conductor__Client
#
# Typed HTTP client for the on-box conductor's suite API. The CLI passthrough
# verbs and both TUIs call this — provider.dispatch() routes through it too. The
# HTTP calls are exercised under the gated deploy tests; parse_status (typed
# reconstruction of a suite snapshot) is pure and unit-tested.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Value           import Safe_Str__Http__Header__Value
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Definition                         import Schema__Suite__Definition
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status                        import Schema__Suite__Run__Status


class Conductor__Client(Type_Safe):                                                 # talks to the conductor suite API
    base_url : Safe_Str__Url                 = None                                 # e.g. http://<public-ip>:PORT
    api_key  : Safe_Str__Http__Header__Value = None                                 # X-API-Key value

    def start_suite(self, suite_definition: Schema__Suite__Definition) -> Schema__Suite__Run__Status:
        return self.parse_status(self._post('/suites', suite_definition.json()))

    def get_suite(self, suite_run_id) -> Schema__Suite__Run__Status:
        return self.parse_status(self._get(f'/suites/{suite_run_id}'))

    def stop_suite(self, suite_run_id) -> Schema__Suite__Run__Status:
        return self.parse_status(self._post(f'/suites/{suite_run_id}/stop', {}))

    def get_flows(self, suite_run_id) -> List[dict]:
        import requests
        response = requests.get(f'{self.base_url}/suites/{suite_run_id}/flows', headers=self._headers(), timeout=30)
        response.raise_for_status()
        return [json.loads(line) for line in response.text.splitlines() if line.strip()]

    # ── pure ───────────────────────────────────────────────────────────────────
    def parse_status(self, data: dict) -> Schema__Suite__Run__Status:
        return Schema__Suite__Run__Status.from_json(data)

    def _headers(self) -> dict:
        return {'X-API-Key': str(self.api_key)} if self.api_key else {}

    # ── HTTP (exercised under the gated deploy tests) ───────────────────────────
    def _get(self, path: str) -> dict:
        import requests
        response = requests.get(f'{self.base_url}{path}', headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, body: dict) -> dict:
        import requests
        response = requests.post(f'{self.base_url}{path}', json=body, headers=self._headers(), timeout=60)
        response.raise_for_status()
        return response.json()
