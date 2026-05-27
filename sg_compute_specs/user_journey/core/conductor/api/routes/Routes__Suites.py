# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Routes__Suites (the conductor suite API)
#
#   POST /suites                              — start a suite from a definition body
#   GET  /suites/{suite_run_id}               — live suite snapshot
#   POST /suites/{suite_run_id}/stop          — stop a running suite
#   GET  /suites/{suite_run_id}/flows         — captured network flows (NDJSON, proxied from the mitmproxy sidecar)
#   POST /suites/{suite_run_id}/report/{wid}  — a worker posts its terminal verdict
#
# Reads the process-singleton SUITE_SERVICE (shared in-process, like the mitmproxy
# RUN_CAPTURE). Its runtime defaults to in-memory; the conductor container swaps in
# the Docker-socket backend at boot. Auth: the standard X-API-Key middleware.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                         import Body, HTTPException, Response
from osbot_fast_api.api.routes.Fast_API__Routes                                      import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix            import Safe_Str__Fast_API__Route__Prefix

import json
import os

from sg_compute_specs.user_journey.core.clients.Mitmproxy__Capture__Client      import Mitmproxy__Capture__Client
from sg_compute_specs.user_journey.core.conductor.Suite__Service                import Suite__Service
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State        import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Definition  import Schema__Suite__Definition


TAG__ROUTES_SUITES   = 'suites'
ROUTES_PATHS__SUITES = ['/suites', '/suites/{suite_run_id}',
                        '/suites/{suite_run_id}/stop', '/suites/{suite_run_id}/scale',
                        '/suites/{suite_run_id}/flows',
                        '/suites/{suite_run_id}/report/{worker_id}']

SUITE_SERVICE = Suite__Service().setup()                                            # process singleton; runtime swapped at boot

CAPTURE_CLIENT = Mitmproxy__Capture__Client()                                       # flows source; tests swap it, boot points it at the sidecar
if os.environ.get('SG_UJ__CAPTURE_URL'):
    CAPTURE_CLIENT.base_url = os.environ['SG_UJ__CAPTURE_URL']
if os.environ.get('SG_UJ__CAPTURE_API_KEY'):
    CAPTURE_CLIENT.api_key  = os.environ['SG_UJ__CAPTURE_API_KEY']


class Routes__Suites(Fast_API__Routes):
    tag : str = TAG__ROUTES_SUITES

    def setup_routes(self):
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')                        # literal paths (no /suites/suites)
        router      = self.router

        @router.post('/suites')
        def start(payload: dict = Body(default=None)):
            definition = Schema__Suite__Definition.from_json(payload or {})
            return SUITE_SERVICE.start_suite(definition).json()

        @router.get('/suites/{suite_run_id}')
        def get(suite_run_id: str):
            status = SUITE_SERVICE.get_suite(suite_run_id)
            if status is None:
                raise HTTPException(status_code=404, detail=f'no suite run {suite_run_id!r}')
            return status.json()

        @router.post('/suites/{suite_run_id}/stop')
        def stop(suite_run_id: str):
            status = SUITE_SERVICE.stop_suite(suite_run_id)
            if status is None:
                raise HTTPException(status_code=404, detail=f'no suite run {suite_run_id!r}')
            return status.json()

        @router.post('/suites/{suite_run_id}/scale')
        def scale(suite_run_id: str, payload: dict = Body(default=None)):
            payload      = payload or {}
            count        = int(payload.get('count', 0))
            concurrency  = int(payload.get('concurrency', 1))
            status       = SUITE_SERVICE.scale_suite(suite_run_id, count, concurrency)
            if status is None:
                raise HTTPException(status_code=404, detail=f'no suite run {suite_run_id!r}')
            return status.json()

        @router.get('/suites/{suite_run_id}/flows')
        def flows(suite_run_id: str):                                               # NDJSON, proxied from the mitmproxy sidecar
            records = CAPTURE_CLIENT.network_log(suite_run_id)
            body    = '\n'.join(json.dumps(record) for record in records)
            return Response(content=body, media_type='application/x-ndjson')

        @router.post('/suites/{suite_run_id}/report/{worker_id}')
        def report(suite_run_id: str, worker_id: str, payload: dict = Body(default=None)):
            state_str = (payload or {}).get('state')
            try:
                state = Enum__Worker__State(state_str)
            except ValueError:
                raise HTTPException(status_code=422, detail=f'bad worker state: {state_str!r}')
            status = SUITE_SERVICE.report_worker(suite_run_id, worker_id, state)
            if status is None:
                raise HTTPException(status_code=404, detail=f'no suite run {suite_run_id!r}')
            return status.json()
