# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Mitm__Flow__Summary
# One-line summary of a mitmweb flow, surfaced by `sp vnc flows <name>` and
# the matching FastAPI route. Per N4 there is no automatic export — flows
# live on the EC2 and die with it; this is just a peek for human debug.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url


class Schema__Vnc__Mitm__Flow__Summary(Type_Safe):
    flow_id        : Safe_Str__Id                                                   # mitmweb's flow id (uuid-ish)
    method         : Safe_Str__Id                                                   # 'GET' / 'POST' / 'CONNECT' / etc.
    url            : Safe_Str__Url
    status_code    : int            = 0                                             # 0 means the flow hasn't completed yet
    intercepted_at : Safe_Str__Text                                                 # ISO-8601 timestamp from mitmproxy
