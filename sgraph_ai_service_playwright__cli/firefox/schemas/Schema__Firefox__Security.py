# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Security
# Request/response for PUT|GET /firefox/{stack_id}/security.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Firefox__Security(Type_Safe):
    self_signed_certs : bool = True    # allow/block self-signed TLS certificates
    ssl_intercept     : bool = False   # mitmproxy SSL interception on/off
