# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Page__Listeners__Buffer (Φ4 — load-time forensics)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.playwright.core.service.Page__Listeners__Buffer import (
    Page__Listeners__Buffer,
    PAGE_ATTR_NAME,
    buffer_from_page,
    safe_str_attr,
    safe_int_attr,
    MAX_EVENTS_PER_KIND,
)


# ── Fake Playwright objects ──────────────────────────────────────────────────

class _Fake_Page:
    def __init__(self):
        self.handlers = {}                                                          # event_name → handler

    def on(self, event_name, handler):
        self.handlers[event_name] = handler

    # Trigger helpers — tests use these to simulate Playwright firing events
    def trigger(self, event_name, *args):
        self.handlers[event_name](*args)


class _Fake_Console_Msg:
    def __init__(self, type='log', text='hello', location=None):
        self.type     = type
        self.text     = text
        self.location = location


class _Fake_Console_Location:
    def __init__(self, url='https://example.com/app.js', lineNumber=42, columnNumber=7):
        self.url          = url
        self.lineNumber   = lineNumber
        self.columnNumber = columnNumber


class _Fake_Request:
    def __init__(self, url='https://example.com/', method='GET', resource_type='document', failure_text=None):
        self.url           = url
        self.method        = method
        self.resource_type = resource_type
        self.failure       = failure_text                                           # simple string for the fake; real Playwright has a Failure object


class _Fake_Response:
    def __init__(self, url='https://example.com/', status=200, request=None):
        self.url     = url
        self.status  = status
        self.request = request


# ── Attach / event handlers ───────────────────────────────────────────────────

class test_attach(TestCase):

    def test__wires_four_listeners_and_sets_page_attr(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page()
        buf.attach(page)
        assert set(page.handlers.keys()) == {'console', 'request', 'response', 'requestfailed'}
        assert getattr(page, PAGE_ATTR_NAME) is buf
        assert buf.attached_to_id == id(page)


class test_console_capture(TestCase):

    def test__captures_minimal_console_event(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        page.trigger('console', _Fake_Console_Msg(type='warn', text='heads up'))
        assert len(buf.console_events) == 1
        e = buf.console_events[0]
        assert e['type'] == 'warn' and e['text'] == 'heads up'
        assert 'timestamp' in e

    def test__captures_location_when_present(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        loc  = _Fake_Console_Location(url='https://example.com/x.js', lineNumber=10, columnNumber=3)
        page.trigger('console', _Fake_Console_Msg(location=loc))
        assert buf.console_events[0]['location'] == {'url': 'https://example.com/x.js', 'lineNumber': 10, 'columnNumber': 3}

    def test__bad_console_event_does_not_crash(self):                                # Defensive — any exception in the handler must be swallowed
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        page.trigger('console', None)                                               # Will trip safe_str_attr
        assert buf.console_events == [] or len(buf.console_events) == 1             # either swallowed or harmless


class test_network_lifecycle(TestCase):

    def test__request_and_response_balance_in_flight(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        req  = _Fake_Request(url='https://example.com/a.css', resource_type='stylesheet')
        page.trigger('request', req)
        assert buf.in_flight_count() == 1
        assert buf.request_events[0]['url'] == 'https://example.com/a.css'
        assert buf.request_events[0]['resource_type'] == 'stylesheet'

        page.trigger('response', _Fake_Response(url='https://example.com/a.css', status=200, request=req))
        assert buf.in_flight_count() == 0
        assert buf.response_events[0]['status'] == 200
        assert buf.response_events[0]['ok']     is True

    def test__failed_request_decrements_in_flight(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        req  = _Fake_Request(url='https://blocked.example/x', failure_text='net::ERR_BLOCKED_BY_CLIENT')
        page.trigger('request', req)
        page.trigger('requestfailed', req)
        assert buf.in_flight_count()        == 0
        assert len(buf.failed_events)       == 1
        assert buf.failed_events[0]['url']  == 'https://blocked.example/x'

    def test__4xx_5xx_response_is_ok_false(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        req  = _Fake_Request()
        page.trigger('request', req)
        page.trigger('response', _Fake_Response(status=404, request=req))
        assert buf.response_events[0]['ok'] is False


class test_ring_buffer_trim(TestCase):

    def test__console_buffer_caps_at_max(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        for i in range(MAX_EVENTS_PER_KIND + 50):
            page.trigger('console', _Fake_Console_Msg(text=f'msg-{i}'))
        assert len(buf.console_events) == MAX_EVENTS_PER_KIND
        assert buf.console_events[-1]['text'] == f'msg-{MAX_EVENTS_PER_KIND + 49}'  # newest preserved


class test_read_helpers(TestCase):

    def test__console_tail_returns_last_n(self):
        buf = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        for i in range(10):
            page.trigger('console', _Fake_Console_Msg(text=f'm-{i}'))
        tail = buf.console_tail(3)
        assert [e['text'] for e in tail] == ['m-7', 'm-8', 'm-9']

    def test__console_tail_zero_returns_empty(self):
        buf = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        page.trigger('console', _Fake_Console_Msg(text='x'))
        assert buf.console_tail(0) == []

    def test__network_snapshot_aggregates_three_kinds(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        req  = _Fake_Request()
        page.trigger('request', req)
        page.trigger('response', _Fake_Response(request=req))
        snap = buf.network_snapshot()
        assert set(snap.keys()) == {'requests', 'responses', 'failed'}
        assert len(snap['requests']) == 1
        assert len(snap['responses']) == 1
        assert snap['failed'] == []


class test_module_helpers(TestCase):

    def test__safe_str_attr_returns_default_on_missing(self):
        assert safe_str_attr(None, 'anything', default='fallback') == 'fallback'
        assert safe_str_attr(_Fake_Request(), 'url') == 'https://example.com/'

    def test__safe_int_attr_returns_default_on_missing(self):
        assert safe_int_attr(None, 'x', default=99) == 99
        assert safe_int_attr(_Fake_Response(status=500), 'status') == 500

    def test__buffer_from_page_reads_attached_buffer(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page()
        assert buffer_from_page(page) is None                                       # Before attach
        buf.attach(page)
        assert buffer_from_page(page) is buf

    def test__buffer_from_page_returns_none_for_unattached_page(self):
        assert buffer_from_page(_Fake_Page()) is None


# ─── Long-living connection types excluded from idle predicate ──────────────────
class test_non_idle_resource_types(TestCase):

    def test__websocket_request_does_not_increment_in_flight(self):                   # Otherwise any SPA with a websocket makes wait_for: network_idle_ms permanently impossible
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        ws_req = _Fake_Request(url='wss://example.com/ws', resource_type='websocket')
        page.trigger('request', ws_req)
        assert buf.in_flight_count() == 0                                              # Not counted toward idle
        assert len(buf.request_events) == 1                                            # Still recorded for diagnostics

    def test__eventsource_request_does_not_increment_in_flight(self):
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        sse_req = _Fake_Request(url='https://example.com/stream', resource_type='eventsource')
        page.trigger('request', sse_req)
        assert buf.in_flight_count() == 0
        assert len(buf.request_events) == 1

    def test__xhr_still_increments_in_flight(self):                                    # Regression — only websocket + eventsource are excluded
        buf  = Page__Listeners__Buffer()
        page = _Fake_Page(); buf.attach(page)
        page.trigger('request', _Fake_Request(url='https://example.com/api', resource_type='xhr'))
        assert buf.in_flight_count() == 1
