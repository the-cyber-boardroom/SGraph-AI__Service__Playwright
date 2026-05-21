# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: CF_TUI__Card (ASCII export / no-TTY fallback)
# Asserts the plain-text card states the source and the real tallies. No textual,
# no rich — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator  import CF_TUI__Aggregator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Card        import CF_TUI__Card


class test_CF_TUI__Card(TestCase):

    def test_card_states_source_and_tallies(self):
        parser = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())
        records, skipped = parser.parse(FIXTURE_TSV)
        snapshot = CF_TUI__Aggregator().aggregate(records, source_label='in-memory (fixtures)', files_sampled=1, lines_skipped=skipped, captured_at=100)
        out = CF_TUI__Card().render(snapshot)
        for token in ('CF Traffic Reality', 'in-memory (fixtures)', 'bot', 'human', 'TOP URIs', '/enhancecp'):
            assert token in out, token
