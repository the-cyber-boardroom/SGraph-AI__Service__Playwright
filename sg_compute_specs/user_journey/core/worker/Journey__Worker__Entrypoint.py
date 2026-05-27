# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Journey__Worker__Entrypoint (the container CMD)
#
# What runs inside a worker container. The Docker runtime injects the run identity +
# the whole journey as SG_UJ__* env vars (env-JSON delivery — no store, no callback),
# so the worker is fully self-contained. run_id_from_env / journey_from_env are pure
# and unit-tested; run() hands off to Journey__Worker; main() is the gated integration
# shim that builds the real Playwright service (needs Chromium) and prints the result.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Definition import Schema__Journey__Definition
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Run_Id        import Run_Id
from sg_compute_specs.user_journey.core.worker.Journey__Worker                        import Journey__Worker


class Journey__Worker__Entrypoint(Type_Safe):

    def run_id_from_env(self, env: dict) -> Run_Id:
        value = env.get('SG_UJ__RUN_ID')
        if not value:
            raise ValueError('SG_UJ__RUN_ID is required')
        return Run_Id(value)

    def journey_from_env(self, env: dict) -> Schema__Journey__Definition:
        raw = env.get('SG_UJ__JOURNEY_JSON')
        if not raw:
            raise ValueError('SG_UJ__JOURNEY_JSON is required')
        return Schema__Journey__Definition.from_json(json.loads(raw))

    def run(self, env: dict, playwright_service, capture_client=None):              # env → run a single journey
        run_id  = self.run_id_from_env(env)
        journey = self.journey_from_env(env)
        return Journey__Worker().run(journey, run_id, playwright_service, capture_client)

    def main(self):                                                                 # gated integration shim (real Chromium)
        import os
        from sg_compute_specs.playwright.core.service.Playwright__Service import Playwright__Service
        result = self.run(dict(os.environ), Playwright__Service())                  # capture_client wired by the deploy harness
        print(json.dumps(result.json()))
        return result
