# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: Screen-5 render (pure) + glyph/sparkline helpers
# Asserts the Traffic Reality markup and the shared presentation helpers. No textual,
# no rich — runs on 3.11 (content is decoupled from the view layer).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator  import CF_TUI__Aggregator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Traffic__Render import traffic_markup
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.widgets.CF_TUI__Glyphs import sparkline, bar, pct, status_style


def fixture_snapshot():
    parser = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())
    records, skipped = parser.parse(FIXTURE_TSV)
    return CF_TUI__Aggregator().aggregate(records, source_label='fixtures', files_sampled=1, lines_skipped=skipped, captured_at=100)


class test_CF_TUI__Glyphs(TestCase):

    def test_sparkline(self):
        assert sparkline([])           == ''
        assert len(sparkline([1, 4, 2, 8])) == 4
        assert sparkline([0, 0, 0])    == '▁▁▁'                                       # flat-zero degrades cleanly
        assert sparkline([5, 5])       == '██'                                        # flat-nonzero → full

    def test_bar(self):
        assert bar(0.0, 10) == '░' * 10
        assert bar(1.0, 10) == '▓' * 10
        assert bar(0.5, 10).count('▓') == 5

    def test_pct(self):
        assert pct(1, 2) == 50
        assert pct(1, 0) == 0                                                          # never divide by zero

    def test_status_style(self):
        assert status_style('2xx') == 'green'
        assert status_style('5xx') == 'red'


class test_traffic_markup(TestCase):

    def test_sections_and_real_values(self):
        out = traffic_markup(fixture_snapshot())
        for token in ('CF Traffic Reality', 'THROUGHPUT', 'BOT vs HUMAN', 'STATUS',
                      'CACHE', 'TOP URIs', 'GEOGRAPHY', 'TOP BOTS',
                      '/enhancecp', '/robots.txt', 'US', 'wpbot'):
            assert token in out, token

    def test_empty_snapshot_renders_zeros_not_fakes(self):
        out = traffic_markup(CF_TUI__Aggregator().aggregate([], captured_at=1))
        assert 'CF Traffic Reality' in out
        assert '(no events)'        in out                                            # honest empty state
