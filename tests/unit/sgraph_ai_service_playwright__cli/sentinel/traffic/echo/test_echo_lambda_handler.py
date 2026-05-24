# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the echo lambda_handler (Function URL + CloudFront events)
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.lambda_handler import handler


class TestFunctionUrlEvent:
    def test_echoes_method_and_path(self):
        event = {'requestContext': {'http': {'method': 'GET', 'path': '/etc/passwd', 'sourceIp': '1.2.3.4'}},
                 'rawQueryString': 'a=1', 'headers': {'user-agent': 'curl'}}
        resp = handler(event)
        assert resp['statusCode'] == 200
        body = json.loads(resp['body'])
        assert body['path'] == '/etc/passwd' and body['querystring'] == 'a=1'

    def test_html_when_requested(self):
        event = {'requestContext': {'http': {'method': 'GET', 'path': '/'}},
                 'rawQueryString': 'format=html', 'headers': {}}
        resp = handler(event)
        assert resp['headers']['Content-Type'] == 'text/html' and '<table' in resp['body']


class TestCloudFrontEvent:
    def test_echoes_cf_request(self):
        event = {'Records': [{'cf': {'request': {'method': 'GET', 'uri': '/wp-login.php', 'querystring': '',
                                                 'headers': {'user-agent': [{'value': 'nikto'}]}}}}]}
        resp = handler(event)
        assert resp['status'] == '200'
        body = json.loads(resp['body'])
        assert body['path'] == '/wp-login.php' and body['headers']['user-agent'] == 'nikto'
