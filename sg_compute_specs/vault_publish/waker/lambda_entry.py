# ═══════════════════════════════════════════════════════════════════════════════
# Waker — lambda_entry
# Plain Lambda handler — no FastAPI, no uvicorn, no LWA needed.
# Lambda Function URL passes HTTP events directly; event already contains
# method, headers, path, and body.  handler(event, context) is the entry point.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from sg_compute_specs.vault_publish.waker.Slug__From_Host                        import Slug__From_Host
from sg_compute_specs.vault_publish.waker.Waker__Handler                         import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context


def handler(event, context):                                                       # Lambda entry point
    headers  = event.get('headers') or {}
    host     = headers.get('host') or headers.get('Host', '')
    slug     = Slug__From_Host().extract(host)
    raw_body = event.get('body') or b''
    if isinstance(raw_body, str):
        raw_body = base64.b64decode(raw_body) if event.get('isBase64Encoded') else raw_body.encode()
    http_ctx = (event.get('requestContext') or {}).get('http', {})
    method   = http_ctx.get('method', 'GET')
    path     = event.get('rawPath', '/')
    qs       = event.get('rawQueryString', '')
    if qs:
        path = path + '?' + qs

    ctx    = Schema__Waker__Request_Context(
        host   = host,
        slug   = str(slug) if slug else '',
        path   = path,
        method = method,
        body   = raw_body if isinstance(raw_body, bytes) else raw_body.encode(),
    )
    result = Waker__Handler().handle(ctx)
    body   = result['body']
    return {
        'statusCode'     : result['status_code'],
        'headers'        : {k: v for k, v in result.get('headers', {}).items()
                            if k.lower() != 'content-length'},
        'body'           : body.decode() if isinstance(body, bytes) else body,
        'isBase64Encoded': False,
    }
