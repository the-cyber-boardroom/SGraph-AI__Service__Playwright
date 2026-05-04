# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Default interceptor addon
#
# Runs for every mitmproxy flow. Purely header manipulation: stamps a
# correlation id + timestamp on the request, echoes the id + elapsed ms
# + service version on the response.
#
# Duck-typed — imports nothing from mitmproxy. The flow parameter has
# .request.headers / .response.headers dict-likes and .metadata dict, all
# of which are populated by mitmproxy at runtime.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import time
from datetime                                                                        import datetime, timezone

from sg_compute_specs.mitmproxy.core.consts.version                                 import version__agent_mitmproxy


HEADER__REQUEST_ID   = 'X-Agent-Mitmproxy-Request-Id'
HEADER__REQUEST_TS   = 'X-Agent-Mitmproxy-Request-Ts'
HEADER__ELAPSED_MS   = 'X-Agent-Mitmproxy-Elapsed-Ms'
HEADER__VERSION      = 'X-Agent-Mitmproxy-Version'

METADATA__REQUEST_ID = 'agent_mitmproxy_request_id'                                 # Underscored — mitmproxy's flow.metadata is a plain dict


class Default_Interceptor:

    def request(self, flow):
        request_id                   = secrets.token_hex(6)                         # 12-char hex — wide enough for dev-scale uniqueness, narrow enough to read
        flow.metadata[METADATA__REQUEST_ID] = request_id
        flow.request.headers[HEADER__REQUEST_ID] = request_id
        flow.request.headers[HEADER__REQUEST_TS] = datetime.now(timezone.utc).isoformat()

    def response(self, flow):
        request_id = flow.metadata.get(METADATA__REQUEST_ID, '')
        flow.response.headers[HEADER__REQUEST_ID] = request_id
        flow.response.headers[HEADER__VERSION   ] = str(version__agent_mitmproxy)
        start_ts = getattr(flow.request, 'timestamp_start', None)                   # mitmproxy stamps this at connection start
        if start_ts is not None:
            elapsed_ms = int((time.time() - start_ts) * 1000)
            flow.response.headers[HEADER__ELAPSED_MS] = str(elapsed_ms)


addons = [Default_Interceptor()]                                                     # mitmweb -s <this file> loads this module-level var
