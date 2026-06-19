# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: interceptor pure logic
# Stdlib-only decision + payload-building logic for the mitmproxy interceptor.
# Dependency-free ON PURPOSE: the stock mitmproxy container has no osbot_utils,
# so active.py imports this module directly. Fully unit-testable without mitmproxy.
#
# The action strings returned here are byte-identical to
# Enum__Content_Proxy__Flow__Action values, so the TUI/source map them 1:1.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime    import datetime, timezone
from pathlib     import Path
from urllib.parse import urlparse


VERSION__INTERCEPTOR = 'v0.2.1'                                                     # cookies only, no path params
ADMIN_PATH_PREFIX    = '/mitm-proxy'                                                # always processed → the injected-UI smoke check
MAGIC_HOSTS          = {'mitm.it'}                                                  # mitmproxy onboarding/cert page — never touch it

STATIC_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',     # images
                     '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',             # fonts / styles
                     '.mp4', '.webm', '.mp3', '.wav',                              # media
                     '.pdf', '.zip', '.tar', '.gz'}                                # documents / archives

PROCESSABLE_RESPONSE_TYPES = ('text/html',)                                         # only HTML gets the transform


def should_process_request(method: str, path: str, host: str = '') -> bool:        # send this request to FastAPI?
    if (host or '').lower() in MAGIC_HOSTS:                                         # let mitmproxy serve mitm.it untouched
        return False
    if (method or '').upper() != 'GET':
        return False
    if (path or '').startswith(ADMIN_PATH_PREFIX):                                  # admin/UI must always reach FastAPI
        return True
    url_path = urlparse(path or '').path.lower()
    ext      = Path(url_path).suffix
    if not ext:
        return True
    return ext not in STATIC_EXTENSIONS


def should_process_response(content_type: str, cached_in_request: bool, host: str = '') -> bool:   # send this response to FastAPI?
    if (host or '').lower() in MAGIC_HOSTS:                                         # leave the mitm.it onboarding page intact
        return False
    if cached_in_request:
        return False
    ct = (content_type or '').lower()
    return any(t in ct for t in PROCESSABLE_RESPONSE_TYPES)


def is_text_content(content_type: str) -> bool:                                    # should the response body be captured?
    ct = (content_type or '').lower()
    return any(t in ct for t in ('text/html', 'text/plain', 'application/json'))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_request_payload(method: str, host: str, path: str, headers: dict,
                          request_count: int = 0, errors_count: int = 0) -> dict:  # → POST /proxy/process-request
    return {'method'       : method                ,
            'host'         : host                  ,
            'path'         : path                  ,
            'original_path': path                  ,
            'headers'      : dict(headers or {})   ,                                # includes Cookie — FastAPI parses it
            'stats'        : {'request_count': request_count,
                              'errors_count' : errors_count ,
                              'timestamp'    : _now_iso()   },
            'version'      : VERSION__INTERCEPTOR  }


def build_response_payload(method: str, host: str, path: str, url: str,
                           req_headers: dict, status_code: int, resp_headers: dict,
                           content_type: str, body: str = None,
                           response_count: int = 0, request_count: int = 0,
                           errors_count: int = 0) -> dict:                          # → POST /proxy/process-response
    payload = {'request' : {'method'       : method               ,
                            'host'         : host                 ,
                            'path'         : path                 ,
                            'original_path': path                 ,
                            'url'          : url                  ,
                            'headers'      : dict(req_headers or {})},              # includes Cookie
               'response': {'status_code' : status_code           ,
                            'headers'     : dict(resp_headers or {}),
                            'content_type': (content_type or '').lower()},
               'stats'   : {'response_count': response_count,
                            'request_count' : request_count ,
                            'errors_count'  : errors_count  ,
                            'timestamp'     : _now_iso()    },
               'version' : VERSION__INTERCEPTOR}
    if body is not None and is_text_content(content_type):
        payload['response']['body']      = body
        payload['response']['body_size'] = len(body)
    return payload


def classify_action(processed: bool, fastapi_connected: bool, blocked: bool = False,
                    cached: bool = False, body_overridden: bool = False) -> str:    # → Enum__Content_Proxy__Flow__Action value
    if not processed:
        return 'skipped'
    if not fastapi_connected:
        return 'fallback'
    if blocked:
        return 'blocked'
    if cached:
        return 'cached'
    if body_overridden:
        return 'injected'
    return 'passed'
