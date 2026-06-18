# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: interceptor pure-logic tests
# No mitmproxy needed — the logic module is stdlib-only.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
import sg_compute_specs.content_proxy.interceptors.Content_Proxy__Interceptor__Logic as L


class test_Content_Proxy__Interceptor__Logic(TestCase):

    # ── should_process_request ──────────────────────────────────────────────
    def test_non_get_skipped(self):
        assert L.should_process_request('POST', '/page')      is False
        assert L.should_process_request('PUT',  '/page')      is False

    def test_admin_path_always_processed(self):
        assert L.should_process_request('GET', '/mitm-proxy')          is True
        assert L.should_process_request('GET', '/mitm-proxy/ui/x.js')  is True      # even a .js under admin

    def test_static_assets_skipped(self):
        for p in ('/app.js', '/style.css', '/logo.png', '/f.woff2', '/movie.mp4'):
            assert L.should_process_request('GET', p) is False, p

    def test_html_and_extensionless_processed(self):
        assert L.should_process_request('GET', '/')              is True
        assert L.should_process_request('GET', '/article/9')     is True
        assert L.should_process_request('GET', '/index.html')    is True            # .html not in static set
        assert L.should_process_request('GET', '/p?x=1')         is True            # query stripped

    # ── should_process_response ─────────────────────────────────────────────
    def test_cached_in_request_skipped(self):
        assert L.should_process_response('text/html', cached_in_request=True) is False

    def test_only_html_processed(self):
        assert L.should_process_response('text/html; charset=utf-8', False) is True
        assert L.should_process_response('application/json', False)         is False
        assert L.should_process_response('image/png', False)               is False

    # ── payload builders ────────────────────────────────────────────────────
    def test_request_payload_includes_cookie(self):
        p = L.build_request_payload('GET', 'news.site', '/9',
                                    {'Cookie': 'mitm-show=1', 'Accept': '*/*'},
                                    request_count=7)
        assert p['method'] == 'GET'
        assert p['host']   == 'news.site'
        assert p['headers']['Cookie'] == 'mitm-show=1'
        assert p['stats']['request_count'] == 7
        assert p['version'] == L.VERSION__INTERCEPTOR

    def test_response_payload_body_only_for_text(self):
        with_body = L.build_response_payload('GET', 'h', '/', 'http://h/', {}, 200, {},
                                             'text/html', body='<html></html>')
        assert with_body['response']['body'] == '<html></html>'
        assert with_body['response']['body_size'] == len('<html></html>')
        no_body = L.build_response_payload('GET', 'h', '/img', 'http://h/img', {}, 200, {},
                                           'image/png', body='binary')
        assert 'body' not in no_body['response']

    # ── classify_action maps 1:1 to the enum ──────────────────────────────────
    def test_classify_action_values_match_enum(self):
        cases = {
            ('skipped')  : L.classify_action(processed=False, fastapi_connected=False),
            ('fallback') : L.classify_action(processed=True,  fastapi_connected=False),
            ('blocked')  : L.classify_action(processed=True,  fastapi_connected=True, blocked=True),
            ('cached')   : L.classify_action(processed=True,  fastapi_connected=True, cached=True),
            ('injected') : L.classify_action(processed=True,  fastapi_connected=True, body_overridden=True),
            ('passed')   : L.classify_action(processed=True,  fastapi_connected=True),
        }
        for expected, actual in cases.items():
            assert actual == expected
            assert Enum__Content_Proxy__Flow__Action(actual).value == expected     # every action string is a valid enum
