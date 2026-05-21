# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — tui debug: Debug__Event_Log + Debug__Panel__Render (pure)
# No textual, no AWS. Covers recording, the bounded ring, error events, and the panel
# markup (escaping + the empty state).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log     import Debug__Event_Log
from sgraph_ai_service_playwright__cli.tui.debug.Debug__Panel__Render import debug_panel_markup


class test_Debug__Event_Log(TestCase):

    def test_record_and_tail(self):
        log = Debug__Event_Log()
        log.record('s3.list', 'list bucket/prefix')
        log.record('s3.get',  'GET key', detail='4.2KB')
        assert log.count() == 2
        assert log.events[0].seq == 0
        assert log.events[1].seq == 1
        assert log.tail(1)[0].category == 's3.get'
        assert log.events[1].detail    == '4.2KB'

    def test_error_event(self):
        log = Debug__Event_Log()
        evt = log.error('s3.get', 'denied')
        assert evt.ok is False

    def test_ring_is_bounded(self):
        log = Debug__Event_Log(max_events=5)
        for i in range(20):
            log.record('ui', f'event {i}')
        assert log.count()        == 5
        assert log.events[-1].message == 'event 19'                                  # newest kept
        assert log.events[0].message  == 'event 15'                                  # oldest trimmed

    def test_clear(self):
        log = Debug__Event_Log()
        log.record('ui', 'x')
        log.clear()
        assert log.count() == 0


class test_debug_panel_markup(TestCase):

    def test_empty(self):
        assert '(no activity yet)' in debug_panel_markup(Debug__Event_Log())

    def test_renders_events_and_escapes(self):
        log = Debug__Event_Log()
        log.record('s3.list', 'list [weird]')
        log.error('s3.get', 'boom')
        out = debug_panel_markup(log)
        assert 'Debug'      in out
        assert 's3.list'    in out
        assert r'\[weird]'  in out                                                   # markup escaped
        assert 'boom'       in out
