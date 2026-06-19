# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: active.py (mitmproxy --scripts entry)
# Thin adapter. ALL transformation logic lives in the FastAPI MITM service; this
# script captures each flow, forwards it to FastAPI, and applies what comes back.
# Pure decision/payload logic lives in Content_Proxy__Interceptor__Logic (stdlib
# only) which is mounted alongside this file and unit-tested without mitmproxy.
#
# Control is via cookies (mitm-show / mitm-inject / mitm-debug) — forwarded to
# FastAPI inside the Cookie header; this script never parses them.
# Stamps x-proxy-action so the TUI/source reads ONE header per flow.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from mitmproxy import http                                                          # provided by the mitmproxy runtime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                      # so the sibling logic module imports
import Content_Proxy__Interceptor__Logic as L                                       # noqa: E402

# ── configuration (doc 03 §1.1) ────────────────────────────────────────────────
REQUEST_ENDPOINT      = '/proxy/process-request'
RESPONSE_ENDPOINT     = '/proxy/process-response'
TIMEOUT               = int(os.environ.get('FASTAPI_TIMEOUT', '90'))
FASTAPI_BASE_URL      = os.environ.get('FASTAPI_BASE_URL', '')
FASTAPI_API_KEY_NAME  = os.environ.get('FASTAPI_API_KEY_NAME',  'x-api-key')        # guarded: never None (doc 03 §9 #1)
FASTAPI_API_KEY_VALUE = os.environ.get('FASTAPI_API_KEY_VALUE', '')

FASTAPI_HEADERS = {'content-type': 'application/json', FASTAPI_API_KEY_NAME: FASTAPI_API_KEY_VALUE}

request_count  = 0
response_count = 0
errors_count   = 0
executor       = ThreadPoolExecutor(max_workers=10)


def call_fastapi_sync(endpoint: str, data: dict):
    url = f'{FASTAPI_BASE_URL}{endpoint}'
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=FASTAPI_HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                return json.loads(resp.read())
    except Exception:
        return None


async def call_fastapi(endpoint: str, data: dict):
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(executor, call_fastapi_sync, endpoint, data)
    except Exception:
        return None


async def request(flow: http.HTTPFlow) -> None:
    global request_count, errors_count
    request_count += 1
    if not L.should_process_request(flow.request.method, flow.request.path, flow.request.pretty_host):
        flow.request.headers['x-proxy-action'] = 'skipped'
        return
    flow.request.headers['x-proxy-request-count'] = str(request_count)
    payload = L.build_request_payload(flow.request.method, flow.request.pretty_host,
                                      flow.request.path, dict(flow.request.headers),
                                      request_count, errors_count)
    mods = await call_fastapi(REQUEST_ENDPOINT, payload)
    if not mods:
        errors_count += 1
        flow.request.headers['x-proxy-status'] = 'fastapi-unavailable'
        flow.request.headers['x-proxy-action'] = 'fallback'
        return
    cached = mods.get('cached_response')
    if cached:
        flow.response = http.Response.make(cached.get('status_code', 200),
                                           (cached.get('body', '') or '').encode('utf-8')
                                           if isinstance(cached.get('body'), str) else cached.get('body', b''),
                                           cached.get('headers', {'content-type': 'text/html'}))
        flow.response.headers['x-proxy-cached-in-request'] = 'true'
        flow.response.headers['x-proxy-action']            = 'cached'
        return
    for k, v in (mods.get('headers_to_add') or {}).items():
        flow.request.headers[k] = str(v)
    for k in (mods.get('headers_to_remove') or []):
        if k in flow.request.headers:
            del flow.request.headers[k]
    if mods.get('block_request'):
        flow.response = http.Response.make(mods.get('block_status', 403),
                                           (mods.get('block_message', 'Blocked by proxy')).encode(),
                                           {'content-type': 'text/plain', 'x-blocked-by': 'content-proxy'})
        flow.response.headers['x-proxy-action'] = 'blocked'
        return
    flow.request.headers['x-proxy-status'] = 'fastapi-connected'


async def response(flow: http.HTTPFlow) -> None:
    global response_count
    response_count += 1
    if flow.response.headers.get('x-proxy-action') in ('cached', 'blocked'):        # already decided in request phase
        return
    cached_in_request = flow.response.headers.get('x-proxy-cached-in-request') == 'true'
    content_type      = flow.response.headers.get('content-type', '')
    if not L.should_process_response(content_type, cached_in_request, flow.request.pretty_host):
        flow.response.headers['x-proxy-action'] = 'skipped'
        return
    flow.response.headers['x-proxy-response-count'] = str(response_count)
    body = None
    if flow.response.content:
        body = flow.response.content.decode('utf-8', errors='ignore')
    payload = L.build_response_payload(flow.request.method, flow.request.pretty_host,
                                       flow.request.path, flow.request.pretty_url,
                                       dict(flow.request.headers), flow.response.status_code,
                                       dict(flow.response.headers), content_type, body,
                                       response_count, request_count, errors_count)
    mods = await call_fastapi(RESPONSE_ENDPOINT, payload)
    body_overridden = False
    if mods:
        if mods.get('override_status'):
            flow.response.status_code = mods['override_status']
        if mods.get('override_content_type'):
            flow.response.headers['content-type'] = mods['override_content_type']
        new_body = mods.get('modified_body')
        if new_body:
            flow.response.content = new_body if isinstance(new_body, bytes) else str(new_body).encode('utf-8')
            flow.response.headers['content-length'] = str(len(flow.response.content))
            body_overridden = True
        for k, v in (mods.get('headers_to_add') or {}).items():
            flow.response.headers[k] = str(v)
        for k in (mods.get('headers_to_remove') or []):
            if k in flow.response.headers:
                del flow.response.headers[k]
        flow.response.headers['x-proxy-status'] = 'fastapi-connected'
    else:
        flow.response.headers['x-proxy-status'] = 'fastapi-unavailable'
    flow.response.headers['x-proxy-action'] = L.classify_action(processed=True,
                                                                fastapi_connected=bool(mods),
                                                                body_overridden=body_overridden)


def done():
    executor.shutdown(wait=False)


print('=' * 60)
print('Content-Proxy interceptor loaded')
print(f'version : {L.VERSION__INTERCEPTOR}')
print(f'fastapi : {FASTAPI_BASE_URL or "(unset)"}')
print('control : cookies (mitm-show / mitm-inject / mitm-debug)')
print('=' * 60)
