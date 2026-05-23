# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — echo lambda_handler
# Lambda / Lambda@Edge adapter for the httpget echo server. Reuses the SAME pure
# Echo__Payload as the local/docker server, so the echo is identical across targets.
# Accepts either a Lambda Function URL / API Gateway v2 event or a CloudFront
# (Lambda@Edge) request event, and returns the matching response shape.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Payload import echo_payload, render_html, wants_html


def _from_function_url(event: dict) -> dict:
    ctx     = event.get('requestContext', {}) or {}
    http    = ctx.get('http', {}) or {}
    headers = event.get('headers', {}) or {}
    return echo_payload(method      = http.get('method', event.get('httpMethod', 'GET')),
                        path        = http.get('path',   event.get('rawPath', '/')),
                        querystring = event.get('rawQueryString', ''),
                        headers     = headers,
                        source_ip   = headers.get('x-forwarded-for', http.get('sourceIp', '')),
                        body        = event.get('body', '') or '')


def handler(event, context=None):
    if 'Records' in event:                                                           # CloudFront / Lambda@Edge request event
        request = event['Records'][0]['cf']['request']
        headers = {k: (v[0]['value'] if v else '') for k, v in (request.get('headers') or {}).items()}
        payload = echo_payload(request.get('method', 'GET'), request.get('uri', '/'),
                               request.get('querystring', ''), headers,
                               headers.get('x-forwarded-for', ''), '', seq=0)
        return {'status': '200', 'statusDescription': 'OK',
                'headers': {'content-type': [{'key': 'Content-Type', 'value': 'application/json'}]},
                'body': json.dumps(payload, indent=2)}

    payload  = _from_function_url(event)                                             # Function URL / API Gateway v2
    qs       = event.get('rawQueryString', '')
    headers  = event.get('headers', {}) or {}
    if wants_html(headers, qs):
        return {'statusCode': 200, 'headers': {'Content-Type': 'text/html'}, 'body': render_html(payload)}
    return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(payload, indent=2)}
