# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Flow__Mapper
# Pure mapper from a raw mitmweb /flows entry → Schema__Content_Proxy__Flow__Summary.
# The action/fastapi_connected fields are derived from the x-proxy-* headers the
# interceptor stamps. No HTTP/AWS — fully unit-testable.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy                 import Enum__Content_Proxy__Proxy
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Flow__Summary     import Schema__Content_Proxy__Flow__Summary


def _header(headers, name: str) -> str:                                            # case-insensitive, handles list-of-pairs or dict
    target = name.lower()
    if isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == target:
                return str(v)
    elif isinstance(headers, (list, tuple)):
        for pair in headers:
            if len(pair) == 2 and str(pair[0]).lower() == target:
                return str(pair[1])
    return ''


def _action(raw: dict) -> Enum__Content_Proxy__Flow__Action:
    req = (raw.get('request')  or {}).get('headers')
    res = (raw.get('response') or {}).get('headers')
    value = _header(res, 'x-proxy-action') or _header(req, 'x-proxy-action') or 'passed'
    try:
        return Enum__Content_Proxy__Flow__Action(value)
    except ValueError:
        return Enum__Content_Proxy__Flow__Action.PASSED


class Content_Proxy__Flow__Mapper(Type_Safe):

    def to_flow_summary(self, raw: dict,
                              via: Enum__Content_Proxy__Proxy = Enum__Content_Proxy__Proxy.INT
                        ) -> Schema__Content_Proxy__Flow__Summary:
        req      = raw.get('request')  or {}
        res      = raw.get('response') or {}
        req_hdrs = req.get('headers')
        res_hdrs = res.get('headers')
        connected = (_header(res_hdrs, 'x-proxy-status') == 'fastapi-connected' or
                     _header(req_hdrs, 'x-proxy-status') == 'fastapi-connected')
        return Schema__Content_Proxy__Flow__Summary(
            via               = via                                              ,
            method            = str(req.get('method', '') or '')                 ,
            host              = str(req.get('host',   '') or '')                 ,
            path              = str(req.get('path',   '') or '')                 ,
            status_code       = int(res.get('status_code', 0) or 0)              ,
            action            = _action(raw)                                     ,
            fastapi_connected = connected                                        ,
            request_id        = _header(req_hdrs, 'x-proxy-request-count')       )
