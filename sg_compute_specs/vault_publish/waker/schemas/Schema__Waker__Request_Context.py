# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Schema__Waker__Request_Context
# Parsed request context passed from the FastAPI route to Waker__Handler.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Waker__Request_Context(Type_Safe):
    host   : str = ''                                                             # Raw Host header value
    slug   : str = ''                                                             # Resolved slug (empty if parse failed)
    path   : str = '/'                                                            # Request path including leading /
    method : str = 'GET'                                                          # HTTP method
    body   : bytes = b''                                                          # Request body (forwarded to vault-app when proxying)
