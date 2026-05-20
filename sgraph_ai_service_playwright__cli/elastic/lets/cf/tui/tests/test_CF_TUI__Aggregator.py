# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: CF_TUI__Aggregator
# Pins records → traffic snapshot using the two real golden CF lines (both wpbot,
# US). No textual, no boto3 — runs on 3.11. Asserts the tallies trace to the parsed
# records and that an empty input yields an all-zero snapshot (no fabrication).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source  import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator  import CF_TUI__Aggregator


def records_from(tsv : str):
    parser = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())
    records, skipped = parser.parse(tsv)
    return records, skipped


class test_CF_TUI__Aggregator(TestCase):

    def setUp(self):
        records, skipped = records_from(FIXTURE_TSV)
        self.snapshot = CF_TUI__Aggregator().aggregate(records,
                                                       source        = Enum__CF_TUI__Source.IN_MEMORY,
                                                       source_label  = 'fixtures',
                                                       files_sampled = 1,
                                                       lines_skipped = skipped,
                                                       captured_at   = 123)

    def test_totals_and_bot_split(self):
        assert self.snapshot.total_events   == 2
        assert self.snapshot.bot_events     == 2                                      # both lines are wpbot (BOT_KNOWN)
        assert self.snapshot.human_events   == 0
        assert self.snapshot.unknown_events == 0
        assert self.snapshot.captured_at    == 123

    def test_cache_and_status(self):
        assert self.snapshot.cache_hits  == 0                                         # FunctionGeneratedResponse + Error are not hits
        assert self.snapshot.cache_other == 2
        labels = {row.label: row.count for row in self.snapshot.status_classes}
        assert labels == {'3xx': 1, '4xx': 1}                                         # 302 + 403

    def test_top_uris_countries_bots(self):
        uris = {row.label for row in self.snapshot.top_uris}
        assert '/enhancecp' in uris and '/robots.txt' in uris
        countries = {row.label: row.count for row in self.snapshot.top_countries}
        assert countries == {'US': 2}
        assert len(self.snapshot.top_bots) == 1
        assert 'wpbot'  in self.snapshot.top_bots[0].label
        assert self.snapshot.top_bots[0].count == 2

    def test_throughput_bucketed_by_minute(self):
        assert len(self.snapshot.throughput) == 1                                     # both events share one minute
        assert self.snapshot.throughput[0].value == 2

    def test_empty_input_is_all_zero(self):
        snap = CF_TUI__Aggregator().aggregate([], captured_at=1)
        assert snap.total_events == 0
        assert len(snap.top_uris)       == 0
        assert len(snap.status_classes) == 0
        assert len(snap.throughput)     == 0
