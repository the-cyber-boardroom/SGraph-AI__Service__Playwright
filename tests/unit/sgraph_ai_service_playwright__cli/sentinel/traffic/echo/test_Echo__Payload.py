# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Echo__Payload (pure; no sockets)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Payload import echo_payload, render_html, wants_html


class TestEchoPayload:
    def test_shape(self):
        p = echo_payload('GET', '/etc/passwd', 'a=1', {'User-Agent': 'curl'}, '1.2.3.4', '', seq=3)
        assert p['method'] == 'GET' and p['path'] == '/etc/passwd' and p['querystring'] == 'a=1'
        assert p['source_ip'] == '1.2.3.4' and p['seq'] == 3
        assert p['headers']['user-agent'] == 'curl'                                  # header keys lower-cased
        assert p['echo'] == 'sg-sentinel-httpget'


class TestRenderHtml:
    def test_html_contains_fields_and_escapes(self):
        out = render_html(echo_payload('GET', '/x<script>', '', {'X-Test': 'a&b'}, '1.2.3.4'))
        assert '<table' in out and '/x&lt;script&gt;' in out                         # path html-escaped
        assert 'a&amp;b' in out


class TestWantsHtml:
    def test_querystring_format_html(self):
        assert wants_html({}, 'format=html') is True

    def test_accept_header(self):
        assert wants_html({'Accept': 'text/html'}, '') is True
        assert wants_html({'Accept': 'application/json'}, '') is False

    def test_default_json(self):
        assert wants_html({}, '') is False
