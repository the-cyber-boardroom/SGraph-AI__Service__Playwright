# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Routes__Capture
#
#   GET /capture/network-log/{run_id} — NDJSON of every flow captured for that
#   X-SG-Run-Id (one JSON object per line). Empty body (200) when the run is
#   unknown. An X-SG-Flow-Count header carries the line count.
#
# Reads RUN_CAPTURE (populated in-process by run_capture_addon). Auth: the
# standard X-API-Key middleware (all routes are protected).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from fastapi.responses                                                               import Response
from osbot_fast_api.api.routes.Fast_API__Routes                                      import Fast_API__Routes

from sg_compute_specs.mitmproxy.core.addons.run_capture_addon                        import RUN_CAPTURE


TAG__ROUTES_CAPTURE   = 'capture'
ROUTES_PATHS__CAPTURE = [f'/{TAG__ROUTES_CAPTURE}/network-log/{{run_id}}']

MEDIA_TYPE__NDJSON    = 'application/x-ndjson'
HEADER__FLOW_COUNT    = 'X-SG-Flow-Count'


class Routes__Capture(Fast_API__Routes):
    tag : str = TAG__ROUTES_CAPTURE

    def setup_routes(self):
        router = self.router                                                        # raw router → path param (mirrors Routes__Web)

        @router.get('/network-log/{run_id}')
        def network_log(run_id: str) -> Response:
            records = RUN_CAPTURE.records_for(run_id)
            body    = '\n'.join(json.dumps(record) for record in records)
            return Response(content    = body                                       ,
                            media_type = MEDIA_TYPE__NDJSON                          ,
                            headers    = {HEADER__FLOW_COUNT: str(len(records))}     )
