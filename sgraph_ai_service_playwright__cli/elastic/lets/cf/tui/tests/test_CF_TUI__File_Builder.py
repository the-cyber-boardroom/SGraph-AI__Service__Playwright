# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: CF_TUI__File_Builder
# Pins gunzipped TSV → Schema__CF_TUI__File_View using the golden lines. No textual,
# no boto3 — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV, LINE_ENHANCECP
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__File_Builder import CF_TUI__File_Builder


def builder():
    return CF_TUI__File_Builder(parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()))


class test_CF_TUI__File_Builder(TestCase):

    def test_build_two_events(self):
        view = builder().build('k.gz', FIXTURE_TSV, size_bytes=1234)
        assert view.key          == 'k.gz'
        assert view.size_bytes   == 1234
        assert view.total_events == 2
        assert view.lines_skipped == 0
        assert len(view.events)  == 2
        assert FIXTURE_TSV.split('\n')[0] in view.raw_text

    def test_event_row_fields(self):
        view = builder().build('k.gz', LINE_ENHANCECP)
        ev   = view.events[0]
        assert ev.method       == 'GET'
        assert ev.status       == 302
        assert ev.status_class == '3xx'
        assert ev.uri          == '/enhancecp'
        assert ev.country      == 'US'
        assert ev.cache_hit    is False
        assert ev.is_bot       is True
        assert 'wpbot' in ev.user_agent
        assert len(ev.time) == 8                                                     # HH:MM:SS

    def test_empty_text(self):
        view = builder().build('k.gz', '')
        assert view.total_events == 0
        assert len(view.events)  == 0

    def test_raw_capped(self):
        many = '\n'.join([LINE_ENHANCECP] * 10)
        view = CF_TUI__File_Builder(parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()), max_raw_lines=3).build('k.gz', many)
        assert 'more lines' in view.raw_text                                         # capped
        assert view.total_events == 10                                               # parsing is not capped, only the raw view
