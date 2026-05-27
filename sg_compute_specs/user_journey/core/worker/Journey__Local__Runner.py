# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Journey__Local__Runner (run ONE journey on this laptop)
#
# The fast feedback loop: load a journey from a JSON file, run it against a real local
# Chromium (the browser is pointed at a local mitmproxy via SG_PLAYWRIGHT__DEFAULT_PROXY_URL
# at launch), then pull that run's captured flows back from the mitmproxy. No conductor,
# no Docker, no AWS. load_journey / new_run_id are pure + unit-tested; run() is the gated
# integration (needs Chromium + a reachable mitmproxy) — the cli `run-local` verb drives it.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import uuid
from pathlib import Path

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Value     import Safe_Str__Http__Header__Value
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                       import Safe_Str__Url

from sg_compute_specs.user_journey.core.clients.Mitmproxy__Capture__Client          import Mitmproxy__Capture__Client
from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Definition import Schema__Journey__Definition
from sg_compute_specs.user_journey.core.worker.Journey__Worker                       import Journey__Worker


class Journey__Local__Runner(Type_Safe):
    capture_url     : Safe_Str__Url                 = None                           # mitmproxy admin (e.g. http://127.0.0.1:8000) — flows source
    capture_api_key : Safe_Str__Http__Header__Value = None

    def load_journey(self, path: str) -> Schema__Journey__Definition:
        return Schema__Journey__Definition.from_json(json.loads(Path(path).read_text(encoding='utf-8')))

    def new_run_id(self) -> str:
        return f'local-{uuid.uuid4().hex[:12]}'

    def capture_client(self):
        client = Mitmproxy__Capture__Client()
        if self.capture_url     is not None: client.base_url = self.capture_url
        if self.capture_api_key is not None: client.api_key  = self.capture_api_key
        return client

    def run(self, journey, run_id) -> tuple:                                         # gated: real Chromium + reachable mitmproxy
        from sg_compute_specs.playwright.core.service.Playwright__Service import Playwright__Service
        capture = self.capture_client() if self.capture_url is not None else None
        result  = Journey__Worker().run(journey, run_id, Playwright__Service(), capture)
        flows   = capture.network_log(run_id) if capture is not None else []
        return (result, flows)

    def run_file(self, path: str, run_id: str = None) -> tuple:                      # load + run → (journey, run_id, result, flows)
        journey       = self.load_journey(path)
        run_id        = run_id or self.new_run_id()
        result, flows = self.run(journey, run_id)
        return (journey, run_id, result, flows)
