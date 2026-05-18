# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Endpoint__Proxy
# Simple urllib3 reverse-proxy. Forwards the request to the vault-app and
# returns the response dict (status, headers, body).
#
# Lambda buffered invoke mode caps responses at 6 MB. The proxy checks and
# returns a 502 with a clear message if the response body exceeds the cap.
# ═══════════════════════════════════════════════════════════════════════════════

import urllib3

from osbot_utils.type_safe.Type_Safe import Type_Safe

MAX_RESPONSE_BYTES = 5 * 1024 * 1024                                              # 5 MB safety margin below Lambda's 6 MB buffered cap

_pool = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=30))


class Endpoint__Proxy(Type_Safe):
    connect_timeout : int = 2
    read_timeout    : int = 30

    def proxy(self, vault_url: str, method: str, path: str,
              headers: dict, body: bytes) -> dict:
        target = vault_url.rstrip('/') + path
        try:
            resp = _pool.request(
                method  = method,
                url     = target,
                body    = body or None,
                headers = {k: v for k, v in (headers or {}).items()
                           if k.lower() not in ('host', 'connection', 'transfer-encoding')},
                preload_content = True,
            )
            if len(resp.data) > MAX_RESPONSE_BYTES:
                return {
                    'status_code': 502,
                    'headers'    : {'Content-Type': 'text/plain'},
                    'body'       : f'Response too large ({len(resp.data)} bytes; cap is {MAX_RESPONSE_BYTES})'.encode(),
                }
            return {
                'status_code': resp.status,
                'headers'    : dict(resp.headers),
                'body'       : resp.data,
            }
        except Exception as e:
            return {
                'status_code': 502,
                'headers'    : {'Content-Type': 'text/plain'},
                'body'       : f'Proxy error: {e}'.encode(),
            }
