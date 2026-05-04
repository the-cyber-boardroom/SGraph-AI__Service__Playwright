# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Audit log addon
#
# One JSON line per completed flow to stdout. Fluent-bit (Phase 3) tails the
# container log, filters for lines starting with '{', and ships them to
# OpenSearch. No buffering — fluentbit-friendly.
#
# Duck-typed — no mitmproxy imports at module load time.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys
from datetime                                                                        import datetime, timezone

from sg_compute_specs.mitmproxy.core.addons.default_interceptor                     import METADATA__REQUEST_ID


class Audit_Log:

    def response(self, flow):
        request  = flow.request
        response = flow.response
        start_ts = getattr(request, 'timestamp_start', None)
        end_ts   = getattr(response, 'timestamp_end' , None) or getattr(response, 'timestamp_start', None)
        elapsed_ms = int((end_ts - start_ts) * 1000) if (start_ts and end_ts) else None

        client_addr = None
        if getattr(flow, 'client_conn', None) is not None:
            peer = getattr(flow.client_conn, 'peername', None)
            if peer and len(peer) >= 1:
                client_addr = peer[0]

        proxy_user = None
        auth_header = request.headers.get('Proxy-Authorization', '') if request.headers else ''
        if auth_header.lower().startswith('basic '):
            import base64
            try:
                decoded    = base64.b64decode(auth_header[6:].encode()).decode('utf-8', 'ignore')
                proxy_user = decoded.split(':', 1)[0] if ':' in decoded else decoded
            except Exception:
                proxy_user = None                                                    # Malformed auth header — leave blank, mitmweb already rejected the flow

        entry = {'ts'            : datetime.now(timezone.utc).isoformat()            ,
                 'flow_id'       : flow.metadata.get(METADATA__REQUEST_ID, '')       ,
                 'method'        : request.method                                    ,
                 'scheme'        : request.scheme                                    ,
                 'host'          : request.host                                      ,
                 'path'          : request.path                                      ,
                 'status'        : response.status_code                              ,
                 'bytes_request' : len(request.content or b'')                       ,
                 'bytes_response': len(response.content or b'')                      ,
                 'elapsed_ms'    : elapsed_ms                                        ,
                 'client_addr'   : client_addr                                       ,
                 'proxy_user'    : proxy_user                                        }

        sys.stdout.write(json.dumps(entry) + '\n')
        sys.stdout.flush()


addons = [Audit_Log()]
