# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Schema__Waker__Request_Context
# Parsed request context passed from the FastAPI route to Waker__Handler.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Waker__Request_Context(Type_Safe):
    host           : str   = ''                                                       # Viewer host used for slug extraction (X-Forwarded-Host if present, else origin Host)
    origin_host    : str   = ''                                                       # Raw HTTP Host header — Lambda URL hostname when called via CloudFront
    forwarded_host : str   = ''                                                       # X-Forwarded-Host (set by a CloudFront Function or reverse proxy)
    slug           : str   = ''                                                       # Resolved slug (empty if parse failed)
    path           : str   = '/'                                                      # Request path including leading /
    method         : str   = 'GET'                                                    # HTTP method
    body           : bytes = b''                                                      # Request body (forwarded to vault-app when proxying)
    request_id     : str   = ''                                                       # Trace / request ID for debug headers + log correlation
    source_ip      : str   = ''                                                       # Client IP from X-Forwarded-For / request.client.host
    proxy_headers  : str   = ''                                                       # Pre-rendered "key: value\n" lines for proxy-related headers (debug only)
