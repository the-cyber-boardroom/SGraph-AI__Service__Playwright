# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__In_Memory_Source
# Data source over real CF log lines held in memory (or read from a local file via
# from_file). Parses with the same CF__Realtime__Log__Parser the LETS events slice
# uses, then aggregates — so it renders identically to the S3 source with no AWS.
# Honest: it parses REAL CloudFront TSV lines; the label says "in-memory (fixtures)"
# so the screen never implies it is live traffic. Used by tests and for demoing the
# screens anywhere (CI, laptop, the SSM/docker chain).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source         import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator         import CF_TUI__Aggregator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Data_Source         import CF_TUI__Data_Source


class CF_TUI__In_Memory_Source(CF_TUI__Data_Source):
    tsv_text     : str                                                               # one or more real CF real-time TSV lines, newline-separated
    source_label : str = 'in-memory (fixtures)'
    aggregator   : CF_TUI__Aggregator
    parser       : CF__Realtime__Log__Parser

    def setup(self):
        if self.parser.bot_classifier is None:
            self.parser.bot_classifier = Bot__Classifier()
        return self

    @classmethod
    def from_file(cls, path : str, source_label : str = ''):                         # load real CF TSV from a local file
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            text = handle.read()
        return cls(tsv_text=text, source_label=source_label or f'file: {path}').setup()

    def source(self) -> Enum__CF_TUI__Source:
        return Enum__CF_TUI__Source.IN_MEMORY

    def label(self) -> str:
        return self.source_label

    def traffic_snapshot(self) -> Schema__CF_TUI__Traffic_Snapshot:
        self.setup()
        records, skipped = self.parser.parse(self.tsv_text)
        files = 1 if self.tsv_text.strip() else 0
        return self.aggregator.aggregate(records,
                                         source        = Enum__CF_TUI__Source.IN_MEMORY,
                                         source_label  = self.source_label,
                                         files_sampled = files,
                                         lines_skipped = skipped,
                                         captured_at   = int(time.time()))
