# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Lambda_To_ASGI
# Minimal Lambda-Function-URL-v2 → ASGI adapter. Lets lambda_entry dispatch
# specific path prefixes (today: /__admin__/*) to a FastAPI app without
# pulling in mangum / aws-lambda-web-adapter / a full uvicorn stack.
#
# Future direction: as more of the waker surface migrates to FastAPI, more
# path prefixes will route through here. Eventually lambda_entry becomes a
# very thin wrapper around `Lambda_To_ASGI(app)(event)` for everything.
#
# Scope shape follows ASGI 3.0 / HTTP scope spec:
#   https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
#
# Response handling:
#   - Multiple Set-Cookie headers are split into the `cookies` array on the
#     Function-URL v2 response (single-header concatenation breaks browser
#     parsing of attributes like Domain/SameSite).
#   - Body is returned as string for text/json/javascript/xml content types,
#     base64-encoded otherwise.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import base64

from osbot_utils.type_safe.Type_Safe import Type_Safe


_TEXTUAL_CT_PREFIXES = ('text/', 'application/json', 'application/javascript',
                        'application/xml', 'application/x-www-form-urlencoded')


class Lambda_To_ASGI(Type_Safe):
    # The ASGI app. Set on construction. Not a Type_Safe field because it's
    # an arbitrary callable; held on a plain instance attribute via __init__.

    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        self._app = app

    def __call__(self, event: dict) -> dict:
        request_ctx = (event.get('requestContext') or {}).get('http', {}) or {}
        headers_in  = event.get('headers') or {}
        cookies_in  = event.get('cookies') or []
        path        = event.get('rawPath', '/') or '/'
        raw_qs      = event.get('rawQueryString', '') or ''
        method      = (request_ctx.get('method') or 'GET').upper()

        raw_body = event.get('body') or ''
        if isinstance(raw_body, str):
            raw_body = (base64.b64decode(raw_body) if event.get('isBase64Encoded')
                        else raw_body.encode())

        # ASGI headers list — [(bytes, bytes)]. Lambda's headers dict already
        # lower-cases keys. Cookies array (if any) is joined into a single
        # Cookie request header (browser sends them that way).
        asgi_headers = [(k.lower().encode(), str(v).encode())
                        for k, v in headers_in.items() if v is not None]
        if cookies_in:
            cookie_value = '; '.join(cookies_in)
            asgi_headers.append((b'cookie', cookie_value.encode()))

        host_hdr = headers_in.get('host', '') or headers_in.get('Host', '') or ''
        scope = {
            'type'         : 'http',
            'asgi'         : {'version': '3.0', 'spec_version': '2.3'},
            'http_version' : '1.1',
            'method'       : method,
            'scheme'       : 'https',
            'path'         : path,
            'raw_path'     : path.encode(),
            'query_string' : raw_qs.encode(),
            'root_path'    : '',
            'headers'      : asgi_headers,
            'client'       : (request_ctx.get('sourceIp', '') or '127.0.0.1', 0),
            'server'       : (host_hdr or 'lambda', 443),
        }

        # Capture the ASGI send() calls.
        response_state = {'status': 200, 'headers': []}
        body_chunks    = []
        body_sent      = {'flag': False}

        async def receive():
            # Single-shot body delivery — Lambda passes the whole request body
            # up front, no streaming.
            if body_sent['flag']:
                return {'type': 'http.disconnect'}
            body_sent['flag'] = True
            return {'type': 'http.request', 'body': raw_body, 'more_body': False}

        async def send(message: dict):
            msg_type = message.get('type', '')
            if msg_type == 'http.response.start':
                response_state['status']  = int(message.get('status', 200))
                response_state['headers'] = list(message.get('headers') or [])
            elif msg_type == 'http.response.body':
                chunk = message.get('body') or b''
                if chunk:
                    body_chunks.append(chunk)

        async def run():
            await self._app(scope, receive, send)

        asyncio.run(run())

        # Split Set-Cookie into the v2 `cookies` array; everything else into
        # the headers dict. Multi-value headers other than Set-Cookie are
        # concatenated with ", " (ASGI emits one tuple per value).
        cookies_out = []
        headers_out = {}
        for k, v in response_state['headers']:
            k_str = k.decode().lower() if isinstance(k, (bytes, bytearray)) else str(k).lower()
            v_str = v.decode()        if isinstance(v, (bytes, bytearray)) else str(v)
            if k_str == 'set-cookie':
                cookies_out.append(v_str)
                continue
            existing = headers_out.get(k_str)
            headers_out[k_str] = f'{existing}, {v_str}' if existing else v_str

        body_bytes = b''.join(body_chunks)
        ct = headers_out.get('content-type', '').lower()
        is_textual = any(ct.startswith(p) for p in _TEXTUAL_CT_PREFIXES)
        if is_textual:
            try:
                body_str = body_bytes.decode('utf-8')
                is_base64 = False
            except UnicodeDecodeError:
                body_str  = base64.b64encode(body_bytes).decode('ascii')
                is_base64 = True
        else:
            body_str  = base64.b64encode(body_bytes).decode('ascii')
            is_base64 = True

        out = {
            'statusCode'     : response_state['status'],
            'headers'        : headers_out,
            'body'           : body_str,
            'isBase64Encoded': is_base64,
        }
        if cookies_out:
            out['cookies'] = cookies_out
        return out
